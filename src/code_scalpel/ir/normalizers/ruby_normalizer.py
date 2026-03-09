"""
Ruby Normalizer - Converts Ruby CST (tree-sitter-ruby) to Unified IR.

[20260304_FEATURE] Ruby language support for surgical extraction and analysis.

Key Mappings:
    program                   -> IRModule
    method                    -> IRFunctionDef  (def foo)
    singleton_method          -> IRFunctionDef  (def self.foo; _metadata["singleton"]=True)
    class                     -> IRClassDef  (class Foo < Bar)
    module                    -> IRClassDef  (module Enum; _metadata["kind"]="module")
    call  (require)           -> IRImport  (require "json")
    call  (include/extend)    -> IRImport  (_metadata["kind"]="mixin")
    call  (attr_accessor/etc) -> list[IRAssign]  (_metadata["kind"]="attr_accessor")
    assignment                -> IRAssign
    operator_assignment       -> IRAugAssign
    return                    -> IRReturn
    if / unless               -> IRIf  (unless negates; _metadata["kind"]="unless")
    while / until             -> IRWhile  (until negates; _metadata["kind"]="until")
    for                       -> IRFor
    call                      -> IRCall
    block                     -> IRFunctionDef  (_metadata["kind"]="block")
    lambda / proc             -> IRFunctionDef  (_metadata["kind"]="lambda"/"proc")
    instance_variable         -> IRName  (@name)
    integer / float           -> IRConstant
    string / simple_symbol    -> IRConstant
    true / false / nil        -> IRConstant
    comment                   -> (skipped)

Tree-sitter field names used:
    method:            name, parameters?, body
    singleton_method:  object, name, parameters?, body
    class:             name, superclass?, body
    module:            name, body
    call:              receiver?, method, arguments?
    assignment:        left, right
    operator_assignment: left, operator, right
    return:            value?
    if/unless:         condition, body, alternative?
    while/until:       condition, body
    for:               pattern, value, body
    block:             call, block_parameters?, body
    lambda:            lambda_parameters?, body

Ruby version: 3.x grammar (tree-sitter-ruby 0.21+)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import tree_sitter_ruby
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
    "**": BinaryOperator.ADD,  # exponentiation — closest approximation
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
    "===": CompareOperator.STRICT_EQ,
    "<=>": CompareOperator.EQ,  # spaceship — closest approximation
    "=~": CompareOperator.EQ,   # regex match — closest approximation
    "!~": CompareOperator.NE,
}

_BOOLOP_MAP: Dict[str, BoolOperator] = {
    "&&": BoolOperator.AND,
    "||": BoolOperator.OR,
    "and": BoolOperator.AND,
    "or": BoolOperator.OR,
    "!": BoolOperator.AND,   # unary not — placeholder
    "not": BoolOperator.AND,
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
    "||=": AugAssignOperator.ADD,  # conditional assign — closest approximation
    "&&=": AugAssignOperator.ADD,
}

# Mixin-type calls that map to IRImport with metadata
_MIXIN_CALLS = {"include", "extend", "prepend"}

# attr_* macro calls that synthesise getter/setter IRAssign nodes
_ATTR_CALLS = {"attr_accessor", "attr_reader", "attr_writer"}

# ---------------------------------------------------------------------------
# Visitor
# ---------------------------------------------------------------------------


class RubyVisitor(TreeSitterVisitor):
    """Visitor that converts tree-sitter Ruby CST nodes to Unified IR."""

    @property
    def language(self) -> str:
        return "ruby"

    def __init__(self, source: str = "") -> None:
        super().__init__()
        self.ctx.source = source
        self._in_class: bool = False  # track whether we are inside a class body

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
    # Module (root)
    # ------------------------------------------------------------------

    def visit_program(self, node: Any) -> IRModule:
        """Top-level Ruby program → IRModule."""
        module = IRModule(
            body=[],
            source_language="ruby",
            loc=self._get_location(node),
        )
        for child in node.named_children:
            result = self.visit(child)
            if result is None:
                continue
            elif isinstance(result, list):
                module.body.extend(result)
            elif isinstance(result, IRNode):
                module.body.append(result)
        return module

    # ------------------------------------------------------------------
    # Method definitions
    # ------------------------------------------------------------------

    def visit_method(self, node: Any) -> IRFunctionDef:
        """
        Ruby instance method → IRFunctionDef.
            def greet(name)
              puts name
            end
        """
        name_node = node.child_by_field_name("name")
        name = self._get_text(name_node) if name_node else "<anon>"

        params = self._visit_method_parameters(node.child_by_field_name("parameters"))
        body = self._visit_body(node.child_by_field_name("body"))

        return IRFunctionDef(
            name=name,
            params=params,
            body=body,
            loc=self._get_location(node),
        )

    def visit_singleton_method(self, node: Any) -> IRFunctionDef:
        """
        Ruby class-level method → IRFunctionDef with metadata["singleton"]=True.
            def self.create(attrs)
              new(attrs)
            end
        """
        name_node = node.child_by_field_name("name")
        name = self._get_text(name_node) if name_node else "<anon>"

        params = self._visit_method_parameters(node.child_by_field_name("parameters"))
        body = self._visit_body(node.child_by_field_name("body"))

        fn = IRFunctionDef(
            name=name,
            params=params,
            body=body,
            loc=self._get_location(node),
        )
        fn._metadata["singleton"] = True  # type: ignore[attr-defined]
        return fn

    # ------------------------------------------------------------------
    # Class / Module definitions
    # ------------------------------------------------------------------

    def visit_class(self, node: Any) -> IRClassDef:
        """
        Ruby class → IRClassDef.
            class User < ActiveRecord::Base
        """
        name_node = node.child_by_field_name("name")
        name = self._get_text(name_node) if name_node else "<anon>"

        # Superclass (inheritance)
        bases: List[IRExpr] = []
        super_node = node.child_by_field_name("superclass")
        if super_node is not None:
            # superclass node wraps the actual name with a '<' token
            for ch in super_node.named_children:
                bases.append(IRName(id=self._get_text(ch), loc=self._get_location(ch)))

        prev_in_class = self._in_class
        self._in_class = True
        body = self._visit_body(node.child_by_field_name("body"))
        self._in_class = prev_in_class

        return IRClassDef(
            name=name,
            bases=bases,
            body=body,
            loc=self._get_location(node),
        )

    def visit_module(self, node: Any) -> IRClassDef:
        """
        Ruby module → IRClassDef with _metadata["kind"]="module".
            module Enumerable
        """
        name_node = node.child_by_field_name("name")
        name = self._get_text(name_node) if name_node else "<anon>"

        prev_in_class = self._in_class
        self._in_class = True
        body = self._visit_body(node.child_by_field_name("body"))
        self._in_class = prev_in_class

        cls = IRClassDef(
            name=name,
            bases=[],
            body=body,
            loc=self._get_location(node),
        )
        cls._metadata["kind"] = "module"  # type: ignore[attr-defined]
        return cls

    # ------------------------------------------------------------------
    # Method calls (require, include, attr_accessor, general calls)
    # ------------------------------------------------------------------

    def visit_call(self, node: Any) -> Optional[Any]:
        """
        Dispatch Ruby method calls:
          - require / require_relative → IRImport
          - include / extend / prepend → IRImport (mixin)
          - attr_accessor/reader/writer → list[IRAssign]
          - general call → IRCall
        """
        method_node = node.child_by_field_name("method")
        if method_node is None:
            # Some call types use the first named child as the method name
            for ch in node.named_children:
                method_node = ch
                break

        method_name = self._get_text(method_node) if method_node else ""

        if method_name in {"require", "require_relative"}:
            return self._visit_require(node, method_name)

        if method_name in _MIXIN_CALLS and self._in_class:
            return self._visit_mixin_call(node, method_name)

        if method_name in _ATTR_CALLS:
            return self._visit_attr_call(node, method_name)

        return self._build_ir_call(node, method_name)

    def _visit_require(self, node: Any, method_name: str) -> IRImport:
        """require 'json' / require_relative './utils' → IRImport."""
        args = self._collect_call_arguments(node)
        module_name = ""
        if args:
            module_name = self._strip_quotes(args[0])
        return IRImport(
            module=module_name,
            names=[],
            loc=self._get_location(node),
        )

    def _visit_mixin_call(self, node: Any, method_name: str) -> IRImport:
        """include Enumerable / extend ClassMethods → IRImport with mixin metadata."""
        args = self._collect_call_arguments(node)
        module_name = args[0] if args else ""
        imp = IRImport(
            module=module_name,
            names=[],
            loc=self._get_location(node),
        )
        imp._metadata["kind"] = "mixin"  # type: ignore[attr-defined]
        imp._metadata["mixin_type"] = method_name  # type: ignore[attr-defined]
        return imp

    def _visit_attr_call(self, node: Any, method_name: str) -> List[IRAssign]:
        """
        attr_accessor :name, :email → list of IRAssign nodes.
        Each symbol arg produces one IRAssign with _metadata["kind"]="attr_accessor".
        """
        assigns: List[IRAssign] = []
        args = self._collect_call_arguments(node)
        for arg in args:
            attr_name = arg.lstrip(":").strip()
            assign = IRAssign(
                targets=[IRName(id=attr_name, loc=self._get_location(node))],
                value=IRConstant(value=None, loc=self._get_location(node)),
                loc=self._get_location(node),
            )
            assign._metadata["kind"] = method_name  # type: ignore[attr-defined]
            assigns.append(assign)
        return assigns

    def _build_ir_call(self, node: Any, method_name: str) -> IRCall:
        """General method call → IRCall."""
        receiver_node = node.child_by_field_name("receiver")
        receiver_text = self._get_text(receiver_node) if receiver_node else None

        full_name = f"{receiver_text}.{method_name}" if receiver_text else method_name

        arg_texts = self._collect_call_arguments(node)
        args: List[IRExpr] = [
            IRConstant(value=a, loc=self._get_location(node)) for a in arg_texts
        ]

        return IRCall(
            func=IRName(id=full_name, loc=self._get_location(node)),
            args=args,
            kwargs={},
            loc=self._get_location(node),
        )

    def _collect_call_arguments(self, node: Any) -> List[str]:
        """Extract argument text strings from a call node's argument_list."""
        arg_list = node.child_by_field_name("arguments")
        if arg_list is None:
            return []
        result: List[str] = []
        for child in arg_list.named_children:
            if child.type in {"(", ")", ","}:
                continue
            result.append(self._get_text(child))
        return result

    def _strip_quotes(self, text: str) -> str:
        """Remove surrounding quotes from a string literal."""
        if len(text) >= 2 and text[0] in ("'", '"') and text[-1] == text[0]:
            return text[1:-1]
        return text

    # ------------------------------------------------------------------
    # Assignments
    # ------------------------------------------------------------------

    def visit_assignment(self, node: Any) -> IRAssign:
        """x = expr → IRAssign."""
        left = node.child_by_field_name("left")
        right = node.child_by_field_name("right")
        target = self._visit_expr(left) if left else IRName(id="<unknown>", loc=None)
        value = self._visit_expr(right) if right else IRConstant(value=None, loc=None)
        return IRAssign(targets=[target], value=value, loc=self._get_location(node))

    def visit_operator_assignment(self, node: Any) -> IRAugAssign:
        """x += expr → IRAugAssign."""
        left = node.child_by_field_name("left")
        right = node.child_by_field_name("right")
        # Operator is a direct child token between left and right
        op_text = ""
        for ch in node.children:
            if not ch.is_named and ch.type not in {"(", ")"}:
                op_text = self._get_text(ch)
                break

        op = _AUG_ASSIGN_MAP.get(op_text, AugAssignOperator.ADD)
        target = self._visit_expr(left) if left else IRName(id="<unknown>", loc=None)
        value = self._visit_expr(right) if right else IRConstant(value=None, loc=None)
        return IRAugAssign(target=target, op=op, value=value, loc=self._get_location(node))

    # ------------------------------------------------------------------
    # Control flow
    # ------------------------------------------------------------------

    def visit_return(self, node: Any) -> IRReturn:
        """return expr → IRReturn."""
        val_node = node.child_by_field_name("value")
        value = self._visit_expr(val_node) if val_node else None
        return IRReturn(value=value, loc=self._get_location(node))

    def visit_if(self, node: Any) -> IRIf:
        """if condition then body [elsif/else] end → IRIf."""
        return self._build_if(node, negate=False)

    def visit_unless(self, node: Any) -> IRIf:
        """unless condition then body [else] end → IRIf with negated condition."""
        ir_if = self._build_if(node, negate=True)
        ir_if._metadata["kind"] = "unless"  # type: ignore[attr-defined]
        return ir_if

    def _build_if(self, node: Any, negate: bool) -> IRIf:
        cond_node = node.child_by_field_name("condition")
        cond_raw = self._visit_expr(cond_node) if cond_node else IRConstant(value=None, loc=None)
        condition: IRExpr = (
            IRBoolOp(op=BoolOperator.AND, values=[cond_raw], loc=self._get_location(node))
            if negate
            else cond_raw
        )

        body_node = node.child_by_field_name("body")
        body = self._visit_body(body_node) if body_node else []

        # else / elsif
        else_body: List[IRNode] = []
        alt_node = node.child_by_field_name("alternative")
        if alt_node is not None:
            for ch in alt_node.named_children:
                r = self.visit(ch)
                if r is None:
                    continue
                elif isinstance(r, list):
                    else_body.extend(r)
                elif isinstance(r, IRNode):
                    else_body.append(r)

        return IRIf(
            test=condition,
            body=body,
            orelse=else_body,
            loc=self._get_location(node),
        )

    def visit_while(self, node: Any) -> IRWhile:
        """while condition do body end → IRWhile."""
        return self._build_while(node, negate=False)

    def visit_until(self, node: Any) -> IRWhile:
        """until condition do body end → IRWhile with negated condition."""
        wh = self._build_while(node, negate=True)
        wh._metadata["kind"] = "until"  # type: ignore[attr-defined]
        return wh

    def _build_while(self, node: Any, negate: bool) -> IRWhile:
        cond_node = node.child_by_field_name("condition")
        cond_raw = self._visit_expr(cond_node) if cond_node else IRConstant(value=None, loc=None)
        condition: IRExpr = (
            IRBoolOp(op=BoolOperator.AND, values=[cond_raw], loc=self._get_location(node))
            if negate
            else cond_raw
        )
        body_node = node.child_by_field_name("body")
        body = self._visit_body(body_node) if body_node else []
        return IRWhile(test=condition, body=body, loc=self._get_location(node))

    def visit_for(self, node: Any) -> IRFor:
        """for x in collection → IRFor."""
        pattern_node = node.child_by_field_name("pattern")
        val_node = node.child_by_field_name("value")
        body_node = node.child_by_field_name("body")

        target = self._visit_expr(pattern_node) if pattern_node else IRName(id="<unknown>", loc=None)
        iter_ = self._visit_expr(val_node) if val_node else IRName(id="<unknown>", loc=None)
        body = self._visit_body(body_node) if body_node else []

        return IRFor(target=target, iter=iter_, body=body, loc=self._get_location(node))

    def visit_break(self, node: Any) -> IRBreak:
        return IRBreak(loc=self._get_location(node))

    def visit_next(self, node: Any) -> IRContinue:
        """Ruby `next` is equivalent to `continue`."""
        return IRContinue(loc=self._get_location(node))

    # ------------------------------------------------------------------
    # Blocks and lambdas
    # ------------------------------------------------------------------

    def visit_block(self, node: Any) -> IRFunctionDef:
        """
        Ruby block (do...end or {...}) → IRFunctionDef with _metadata["kind"]="block".
        """
        params = self._visit_block_parameters(node.child_by_field_name("parameters"))
        body = self._visit_body(node.child_by_field_name("body"))
        fn = IRFunctionDef(
            name="<block>",
            params=params,
            body=body,
            loc=self._get_location(node),
        )
        fn._metadata["kind"] = "block"  # type: ignore[attr-defined]
        return fn

    def visit_do_block(self, node: Any) -> IRFunctionDef:
        """do...end block variant."""
        params = self._visit_block_parameters(node.child_by_field_name("block_parameters"))
        body = self._visit_body(node.child_by_field_name("body"))
        fn = IRFunctionDef(
            name="<block>",
            params=params,
            body=body,
            loc=self._get_location(node),
        )
        fn._metadata["kind"] = "block"  # type: ignore[attr-defined]
        return fn

    def visit_lambda(self, node: Any) -> IRFunctionDef:
        """-> (x) { x + 1 } → IRFunctionDef with _metadata["kind"]="lambda"."""
        params = self._visit_lambda_parameters(node.child_by_field_name("lambda_parameters"))
        body = self._visit_body(node.child_by_field_name("body"))
        fn = IRFunctionDef(
            name="<lambda>",
            params=params,
            body=body,
            loc=self._get_location(node),
        )
        fn._metadata["kind"] = "lambda"  # type: ignore[attr-defined]
        return fn

    # ------------------------------------------------------------------
    # Expression visitors
    # ------------------------------------------------------------------

    def _visit_expr(self, node: Any) -> IRExpr:
        """
        Dispatch an expression node to the appropriate IR expression.
        Falls back to IRName(id=text) for unrecognised nodes.
        """
        if node is None:
            return IRConstant(value=None, loc=None)
        result = self.visit(node)
        if isinstance(result, IRExpr):
            return result
        # Fallback — represent as a name/constant
        return IRName(id=self._get_text(node), loc=self._get_location(node))

    def visit_identifier(self, node: Any) -> IRName:
        return IRName(id=self._get_text(node), loc=self._get_location(node))

    def visit_constant(self, node: Any) -> IRName:
        """Ruby constant (e.g. MyClass) → IRName."""
        return IRName(id=self._get_text(node), loc=self._get_location(node))

    def visit_instance_variable(self, node: Any) -> IRName:
        """@name → IRName."""
        return IRName(id=self._get_text(node), loc=self._get_location(node))

    def visit_class_variable(self, node: Any) -> IRName:
        """@@counter → IRName."""
        return IRName(id=self._get_text(node), loc=self._get_location(node))

    def visit_global_variable(self, node: Any) -> IRName:
        """$stderr → IRName."""
        return IRName(id=self._get_text(node), loc=self._get_location(node))

    def visit_integer(self, node: Any) -> IRConstant:
        try:
            val: Any = int(self._get_text(node).replace("_", ""))
        except ValueError:
            val = self._get_text(node)
        return IRConstant(value=val, loc=self._get_location(node))

    def visit_float(self, node: Any) -> IRConstant:
        try:
            val: Any = float(self._get_text(node).replace("_", ""))
        except ValueError:
            val = self._get_text(node)
        return IRConstant(value=val, loc=self._get_location(node))

    def visit_string(self, node: Any) -> IRConstant:
        return IRConstant(value=self._get_text(node), loc=self._get_location(node))

    def visit_simple_symbol(self, node: Any) -> IRConstant:
        """:name → IRConstant(value=":name")."""
        return IRConstant(value=self._get_text(node), loc=self._get_location(node))

    def visit_true(self, node: Any) -> IRConstant:
        return IRConstant(value=True, loc=self._get_location(node))

    def visit_false(self, node: Any) -> IRConstant:
        return IRConstant(value=False, loc=self._get_location(node))

    def visit_nil(self, node: Any) -> IRConstant:
        return IRConstant(value=None, loc=self._get_location(node))

    def visit_self(self, node: Any) -> IRName:
        return IRName(id="self", loc=self._get_location(node))

    def visit_binary(self, node: Any) -> IRExpr:
        """Binary expression → IRBinaryOp / IRCompare / IRBoolOp."""
        left_node = node.child_by_field_name("left")
        right_node = node.child_by_field_name("right")
        op_node = node.child_by_field_name("operator")

        left = self._visit_expr(left_node)
        right = self._visit_expr(right_node)
        op_text = self._get_text(op_node) if op_node else ""

        if op_text in _BOOLOP_MAP:
            return IRBoolOp(
                op=_BOOLOP_MAP[op_text],
                values=[left, right],
                loc=self._get_location(node),
            )
        if op_text in _COMPARE_MAP:
            return IRCompare(
                left=left,
                ops=[_COMPARE_MAP[op_text]],
                comparators=[right],
                loc=self._get_location(node),
            )
        return IRBinaryOp(
            left=left,
            op=_BINOP_MAP.get(op_text, BinaryOperator.ADD),
            right=right,
            loc=self._get_location(node),
        )

    def visit_unary(self, node: Any) -> IRExpr:
        """Unary expression — return the operand for simplicity."""
        operand_node = node.child_by_field_name("operand")
        return self._visit_expr(operand_node)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _visit_body(self, node: Any) -> List[IRNode]:
        """Visit a body / then / do node, collecting all IR results."""
        if node is None:
            return []
        result: List[IRNode] = []
        for child in node.named_children:
            r = self.visit(child)
            if r is None:
                continue
            elif isinstance(r, list):
                result.extend(r)
            elif isinstance(r, IRNode):
                result.append(r)
        return result

    def _visit_method_parameters(self, node: Any) -> List[IRParameter]:
        """Parse a method's parameters"""
        if node is None:
            return []
        params: List[IRParameter] = []
        for child in node.named_children:
            param_name = ""
            default_val: Optional[str] = None
            if child.type in {"identifier", "simple_symbol"}:
                param_name = self._get_text(child)
            elif child.type in {"optional_parameter", "optional_argument"}:
                name_node = child.child_by_field_name("name")
                val_node = child.child_by_field_name("value")
                param_name = self._get_text(name_node) if name_node else ""
                default_val = self._get_text(val_node) if val_node else None
            elif child.type in {"splat_parameter", "block_parameter", "hash_splat_parameter"}:
                # *args, &block, **kwargs
                for sub in child.named_children:
                    if sub.type == "identifier":
                        param_name = self._get_text(sub)
                        break
                if not param_name:
                    param_name = self._get_text(child)
            else:
                param_name = self._get_text(child)

            if param_name:
                params.append(
                    IRParameter(
                        name=param_name,
                        default=IRConstant(value=default_val, loc=self._get_location(child))
                        if default_val is not None
                        else None,
                        loc=self._get_location(child),
                    )
                )
        return params

    def _visit_block_parameters(self, node: Any) -> List[IRParameter]:
        """Parse block parameters (|x, y|)."""
        if node is None:
            return []
        params: List[IRParameter] = []
        for child in node.named_children:
            if child.type == "identifier":
                params.append(
                    IRParameter(name=self._get_text(child), loc=self._get_location(child))
                )
        return params

    def _visit_lambda_parameters(self, node: Any) -> List[IRParameter]:
        """Parse lambda parameters -> (x, y) { ... }."""
        if node is None:
            return []
        return self._visit_block_parameters(node)

    # expression_statement wrapper
    def visit_expression_statement(self, node: Any) -> Any:
        """Unwrap expression_statement → visit its child."""
        for child in node.named_children:
            return self.visit(child)
        return None


# ---------------------------------------------------------------------------
# Normalizer
# ---------------------------------------------------------------------------


class RubyNormalizer(BaseNormalizer):
    """
    Normalizer for Ruby source code.

    [20260304_FEATURE] Converts tree-sitter Ruby CST to Unified IR.

    Usage::

        from code_scalpel.ir.normalizers.ruby_normalizer import RubyNormalizer

        n = RubyNormalizer()
        module = n.normalize('def hello; puts "hi"; end')
    """

    @property
    def language(self) -> str:
        """[20260304_FEATURE] Language identifier for Ruby normalizer."""
        return "ruby"

    def normalize(self, source: str, filename: str = "<string>") -> IRModule:
        """Parse Ruby source and return an IRModule."""
        language = Language(tree_sitter_ruby.language())
        parser = Parser(language)
        tree = parser.parse(bytes(source, "utf-8"))
        visitor = RubyVisitor(source=source)
        module = visitor.visit(tree.root_node)
        if module is None:
            return IRModule(body=[], source_language="ruby")
        cast_module: IRModule = module  # type: ignore[assignment]
        cast_module._metadata["source_file"] = filename
        return cast_module

    def normalize_node(self, node: Any) -> None:
        """[20260304_FEATURE] Node-level dispatch not needed; visitor handles traversal."""
        return None
