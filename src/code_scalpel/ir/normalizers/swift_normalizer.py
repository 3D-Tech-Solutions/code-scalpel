"""
Swift Normalizer — Converts Swift CST (tree-sitter-swift) to Unified IR.

[20260304_FEATURE] Swift language support for surgical extraction and analysis.

Key Mappings:
    source_file                  -> IRModule
    import_declaration           -> IRImport          (import Foundation)
    class_declaration (class)    -> IRClassDef        (class Foo: Bar)
    class_declaration (struct)   -> IRClassDef        (_metadata["kind"]="struct")
    class_declaration (enum)     -> IRClassDef        (_metadata["kind"]="enum")
    protocol_declaration         -> IRClassDef        (_metadata["kind"]="protocol")
    function_declaration         -> IRFunctionDef     (func foo(...) -> T)
    init_declaration             -> IRFunctionDef     (init(...); name="init")
    property_declaration         -> IRAssign          (var/let x = expr)
    assignment                   -> IRAugAssign (+=)  or  IRAssign (=)
    if_statement                 -> IRIf
    for_statement                -> IRFor             (for x in collection)
    while_statement              -> IRWhile
    guard_statement              -> IRIf              (_metadata["kind"]="guard")
    control_transfer_statement   -> IRReturn / IRBreak / IRContinue
    call_expression              -> IRCall
    lambda_literal               -> IRFunctionDef     (_metadata["kind"]="closure")
    simple_identifier            -> IRName
    integer_literal              -> IRConstant
    real_literal                 -> IRConstant
    boolean_literal              -> IRConstant
    nil                          -> IRConstant
    line_string_literal          -> IRConstant

Tree-sitter field names used:
    class_declaration:     name (type_identifier), body (class_body / enum_class_body)
    function_declaration:  name (simple_identifier), body (function_body),
                           return_type (user_type)
    init_declaration:      name, body (function_body)
    property_declaration:  name (pattern), value (literal/expr)
    if_statement:          condition (expression)
    while_statement:       condition (expression)
    for_statement:         pattern (loop var) — iter and body from positional children
    parameter:             name (simple_identifier), type (user_type)
    assignment:            operator from non-named children; LHS/RHS from named children

Swift version: Swift 5.x grammar (tree-sitter-swift 0.0.1+)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import tree_sitter_swift
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
    "===": CompareOperator.STRICT_EQ,
    "!==": CompareOperator.NE,
    "~=": CompareOperator.EQ,  # pattern-match operator — approximate
}

_BOOLOP_MAP: Dict[str, BoolOperator] = {
    "&&": BoolOperator.AND,
    "||": BoolOperator.OR,
    "!": BoolOperator.AND,  # unary not — placeholder
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

# Swift declaration keywords used to tag IRClassDef metadata
_CLASS_KEYWORDS = {"class", "struct", "enum", "actor"}


# ---------------------------------------------------------------------------
# Visitor
# ---------------------------------------------------------------------------


class SwiftVisitor(TreeSitterVisitor):
    """Visitor that converts tree-sitter Swift CST nodes to Unified IR.

    [20260304_FEATURE] Handles Swift 5.x grammar nodes from tree-sitter-swift.
    """

    @property
    def language(self) -> str:
        return "swift"

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
    # Module (root)
    # ------------------------------------------------------------------

    def visit_source_file(self, node: Any) -> IRModule:
        """Top-level Swift source file → IRModule."""
        module = IRModule(
            body=[],
            source_language="swift",
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
    # Imports
    # ------------------------------------------------------------------

    def visit_import_declaration(self, node: Any) -> IRImport:
        """
        import Foundation / import UIKit.Foo → IRImport.

        The module path is assembled from identifier children.
        """
        parts: List[str] = []
        for child in node.named_children:
            # identifier → simple_identifier chain
            t = child.type
            if t in {"identifier", "simple_identifier", "type_identifier"}:
                parts.append(self._get_text(child))

        # Flatten nested simple_identifier nodes (dotted paths)
        if not parts:
            # Fall back to raw text after "import "
            raw = self._get_text(node)
            module_name = raw.replace("import ", "", 1).strip()
        else:
            # The first identifier child may itself contain simple_identifier children
            root = node.named_children[0] if node.named_children else None
            if root and root.named_children:
                parts = [
                    self._get_text(ch) for ch in root.named_children if ch.is_named
                ]
            module_name = ".".join(parts) if parts else ""

        return IRImport(
            module=module_name,
            names=[],
            loc=self._get_location(node),
        )

    # ------------------------------------------------------------------
    # Type declarations (class / struct / enum / actor)
    # ------------------------------------------------------------------

    def visit_class_declaration(self, node: Any) -> IRClassDef:
        """
        Swift class, struct, enum, or actor declaration → IRClassDef.

        The declaration keyword (class/struct/enum/actor) is stored in
        _metadata["kind"]. Body may be class_body or enum_class_body.
        """
        # Determine keyword (class/struct/enum/actor) from non-named tokens
        kind = "class"
        for ch in node.children:
            if not ch.is_named and ch.type in _CLASS_KEYWORDS:
                kind = ch.type
                break
            elif not ch.is_named and self._get_text(ch) in _CLASS_KEYWORDS:
                kind = self._get_text(ch)
                break

        name_node = node.child_by_field_name("name")
        name = self._get_text(name_node) if name_node else "<anon>"

        # Superclass / conformances from type_annotation / inheritance_specifier
        bases: List[IRExpr] = []
        for ch in node.named_children:
            if ch.type in {"type_inheritance_clause", "inheritance_clause"}:
                for sub in ch.named_children:
                    bases.append(
                        IRName(id=self._get_text(sub), loc=self._get_location(sub))
                    )

        body_node = node.child_by_field_name("body")
        body = self._visit_type_body(body_node)

        cls = IRClassDef(
            name=name,
            bases=bases,
            body=body,
            loc=self._get_location(node),
        )
        cls._metadata["kind"] = kind  # type: ignore[attr-defined]
        return cls

    def visit_protocol_declaration(self, node: Any) -> IRClassDef:
        """protocol Drawable { func draw() } → IRClassDef(kind="protocol")."""
        # Name is the type_identifier child
        name = "<anon>"
        for ch in node.named_children:
            if ch.type == "type_identifier":
                name = self._get_text(ch)
                break

        body_node = None
        for ch in node.named_children:
            if ch.type == "protocol_body":
                body_node = ch
                break

        body = self._visit_type_body(body_node)
        cls = IRClassDef(
            name=name,
            bases=[],
            body=body,
            loc=self._get_location(node),
        )
        cls._metadata["kind"] = "protocol"  # type: ignore[attr-defined]
        return cls

    def _visit_type_body(self, node: Any) -> List[IRNode]:
        """Visit a class/struct/protocol/enum body node."""
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

    # ------------------------------------------------------------------
    # Function declarations
    # ------------------------------------------------------------------

    def visit_function_declaration(self, node: Any) -> IRFunctionDef:
        """
        func foo(bar: Int) -> String { ... } → IRFunctionDef.

        Static/class modifiers are detected in _metadata["modifiers"].
        """
        name_node = node.child_by_field_name("name")
        name = self._get_text(name_node) if name_node else "<anon>"

        params = self._collect_parameters(node)
        body = self._visit_function_body(node.child_by_field_name("body"))

        fn = IRFunctionDef(
            name=name,
            params=params,
            body=body,
            loc=self._get_location(node),
        )

        # Detect static/class/override modifiers
        modifiers: List[str] = []
        for ch in node.named_children:
            if ch.type == "modifiers":
                modifiers.append(self._get_text(ch))
        if modifiers:
            fn._metadata["modifiers"] = " ".join(modifiers)  # type: ignore[attr-defined]

        return fn

    def visit_init_declaration(self, node: Any) -> IRFunctionDef:
        """
        init(name: String) { ... } → IRFunctionDef(name="init").
        """
        params = self._collect_parameters(node)
        body = self._visit_function_body(node.child_by_field_name("body"))

        fn = IRFunctionDef(
            name="init",
            params=params,
            body=body,
            loc=self._get_location(node),
        )
        fn._metadata["kind"] = "init"  # type: ignore[attr-defined]
        return fn

    def visit_deinit_declaration(self, node: Any) -> IRFunctionDef:
        """deinit { ... } → IRFunctionDef(name="deinit")."""
        body = self._visit_function_body(node.child_by_field_name("body"))
        fn = IRFunctionDef(
            name="deinit",
            params=[],
            body=body,
            loc=self._get_location(node),
        )
        fn._metadata["kind"] = "deinit"  # type: ignore[attr-defined]
        return fn

    def visit_protocol_function_declaration(self, node: Any) -> IRFunctionDef:
        """Protocol method stub → IRFunctionDef with empty body."""
        name_node = node.child_by_field_name("name")
        name = self._get_text(name_node) if name_node else "<anon>"
        params = self._collect_parameters(node)
        fn = IRFunctionDef(
            name=name,
            params=params,
            body=[],
            loc=self._get_location(node),
        )
        fn._metadata["kind"] = "protocol_requirement"  # type: ignore[attr-defined]
        return fn

    def _collect_parameters(self, node: Any) -> List[IRParameter]:
        """Collect all `parameter` named children from a function/init node."""
        params: List[IRParameter] = []
        for ch in node.named_children:
            if ch.type == "parameter":
                param = self._visit_parameter(ch)
                if param is not None:
                    params.append(param)
        return params

    def _visit_parameter(self, node: Any) -> Optional[IRParameter]:
        """parameter node → IRParameter (internal name, optional default)."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            # Fall back to first simple_identifier named child
            for ch in node.named_children:
                if ch.type == "simple_identifier":
                    name_node = ch
                    break
        if name_node is None:
            return None

        name = self._get_text(name_node)

        # Default value may appear as a sibling of the parameter (Swift grammar quirk).
        # We don't reliably extract it here; record as None.
        return IRParameter(
            name=name,
            default=None,
            loc=self._get_location(node),
        )

    def _visit_function_body(self, node: Any) -> List[IRNode]:
        """function_body → visit its `statements` child."""
        if node is None:
            return []
        # function_body has a `statements` named child (or direct children)
        stmts_node = None
        for ch in node.named_children:
            if ch.type == "statements":
                stmts_node = ch
                break
        if stmts_node is not None:
            return self._visit_stmts(stmts_node)
        # Fall back: treat all named children as body
        return self._visit_body_children(node)

    def _visit_stmts(self, node: Any) -> List[IRNode]:
        """statements node → list of IRNode."""
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

    def _visit_body_children(self, node: Any) -> List[IRNode]:
        """Generic body traversal for nodes without a statements wrapper."""
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

    # ------------------------------------------------------------------
    # Properties / variable bindings
    # ------------------------------------------------------------------

    def visit_property_declaration(self, node: Any) -> IRAssign:
        """
        var x: Int = 42 / let name = "Swift" → IRAssign.

        The binding keyword (var/let) is stored in _metadata["binding"].
        """
        # Name comes from the `pattern` field's simple_identifier child
        name_node = node.child_by_field_name("name")
        if name_node is None:
            # Try to find the pattern node
            for ch in node.named_children:
                if ch.type == "pattern":
                    name_node = ch
                    break

        name_text = "<unknown>"
        if name_node is not None:
            # pattern → simple_identifier
            if name_node.type == "pattern":
                for sub in name_node.named_children:
                    if sub.type == "simple_identifier":
                        name_text = self._get_text(sub)
                        break
                if name_text == "<unknown>":
                    name_text = self._get_text(name_node)
            else:
                name_text = self._get_text(name_node)

        target = IRName(
            id=name_text,
            loc=self._get_location(name_node) if name_node else None,
        )

        val_node = node.child_by_field_name("value")
        value: IRExpr
        if val_node is not None:
            value = self._visit_expr(val_node)
        else:
            value = IRConstant(value=None, loc=self._get_location(node))

        assign = IRAssign(
            targets=[target],
            value=value,
            loc=self._get_location(node),
        )

        # Detect var vs let
        binding = "var"
        for ch in node.named_children:
            if ch.type == "value_binding_pattern":
                binding = self._get_text(ch)
                break
        assign._metadata["binding"] = binding  # type: ignore[attr-defined]
        return assign

    # ------------------------------------------------------------------
    # Assignments
    # ------------------------------------------------------------------

    def visit_assignment(self, node: Any) -> Any:
        """
        x = expr  or  x += expr → IRAssign / IRAugAssign.

        The assignment operator is a non-named child token between LHS and RHS.
        """
        named = node.named_children
        if len(named) < 2:
            return None

        lhs_node = named[0]  # directly_assignable_expression
        rhs_node = named[-1]

        # Find operator among non-named children
        op_text = "="
        for ch in node.children:
            if not ch.is_named:
                t = self._get_text(ch)
                if t.endswith("=") and t != "==" and t != "!=":
                    op_text = t
                    break

        target = self._visit_expr(lhs_node)
        value = self._visit_expr(rhs_node)

        if op_text in _AUG_ASSIGN_MAP:
            return IRAugAssign(
                target=target,
                op=_AUG_ASSIGN_MAP[op_text],
                value=value,
                loc=self._get_location(node),
            )

        return IRAssign(
            targets=[target],
            value=value,
            loc=self._get_location(node),
        )

    # ------------------------------------------------------------------
    # Control flow
    # ------------------------------------------------------------------

    def visit_if_statement(self, node: Any) -> IRIf:
        """
        if condition { body } [else { orelse }] → IRIf.

        Handles else-if chains: the else clause is another if_statement child.
        """
        cond_node = node.child_by_field_name("condition")
        condition: IRExpr
        if cond_node is not None:
            condition = self._visit_expr(cond_node)
        else:
            # condition may be the first named child
            condition = IRConstant(value=None, loc=None)

        body: List[IRNode] = []
        else_body: List[IRNode] = []

        named = node.named_children
        # Skip condition node; first statements = body; after 'else' node = orelse
        found_body = False
        past_else = False

        for ch in named:
            if cond_node is not None and ch is cond_node:
                continue
            if ch.type == "else":
                past_else = True
                continue
            if not found_body and not past_else:
                if ch.type == "statements":
                    body = self._visit_stmts(ch)
                    found_body = True
                elif ch.type not in {
                    "comparison_expression",
                    "conjunction_expression",
                    "disjunction_expression",
                    "boolean_literal",
                    "availability_condition",
                }:
                    # Might be the condition expression if no field name matched
                    if not found_body and condition == IRConstant(value=None, loc=None):
                        condition = self._visit_expr(ch)
            elif past_else:
                if ch.type == "if_statement":
                    r = self.visit(ch)
                    if r is not None:
                        else_body = [r] if isinstance(r, IRNode) else r
                elif ch.type == "statements":
                    else_body = self._visit_stmts(ch)

        return IRIf(
            test=condition,
            body=body,
            orelse=else_body,
            loc=self._get_location(node),
        )

    def visit_guard_statement(self, node: Any) -> IRIf:
        """
        guard condition else { ... } → IRIf(kind="guard").

        The guard body (statements after else) maps to IRIf.orelse.
        """
        cond_node = node.child_by_field_name("condition")
        condition: IRExpr = (
            self._visit_expr(cond_node)
            if cond_node is not None
            else IRConstant(value=None, loc=None)
        )

        else_body: List[IRNode] = []
        past_else = False
        for ch in node.named_children:
            if ch.type == "else":
                past_else = True
                continue
            if past_else and ch.type == "statements":
                else_body = self._visit_stmts(ch)

        ir_if = IRIf(
            test=condition,
            body=[],
            orelse=else_body,
            loc=self._get_location(node),
        )
        ir_if._metadata["kind"] = "guard"  # type: ignore[attr-defined]
        return ir_if

    def visit_while_statement(self, node: Any) -> IRWhile:
        """while condition { body } → IRWhile."""
        cond_node = node.child_by_field_name("condition")
        condition: IRExpr = (
            self._visit_expr(cond_node)
            if cond_node is not None
            else IRConstant(value=None, loc=None)
        )

        body: List[IRNode] = []
        for ch in node.named_children:
            if ch.type == "statements":
                body = self._visit_stmts(ch)
                break

        return IRWhile(test=condition, body=body, loc=self._get_location(node))

    def visit_repeat_while_statement(self, node: Any) -> IRWhile:
        """repeat { body } while condition → IRWhile(kind="repeat")."""
        cond_node = node.child_by_field_name("condition")
        condition: IRExpr = (
            self._visit_expr(cond_node)
            if cond_node is not None
            else IRConstant(value=None, loc=None)
        )

        body: List[IRNode] = []
        for ch in node.named_children:
            if ch.type == "statements":
                body = self._visit_stmts(ch)
                break

        wh = IRWhile(test=condition, body=body, loc=self._get_location(node))
        wh._metadata["kind"] = "repeat"  # type: ignore[attr-defined]
        return wh

    def visit_for_statement(self, node: Any) -> IRFor:
        """for x in collection { body } → IRFor."""
        pattern_node = node.child_by_field_name("pattern")

        named = node.named_children
        # [0] = pattern, [1] = iter expression, [-1] = statements (body)
        target: IRExpr
        if pattern_node is not None:
            target = self._visit_expr(pattern_node)
        elif named:
            target = self._visit_expr(named[0])
        else:
            target = IRName(id="<unknown>", loc=None)

        iter_: IRExpr = IRName(id="<unknown>", loc=None)
        body: List[IRNode] = []

        # Collect iter expression (second positional named child) and body
        for i, ch in enumerate(named):
            if pattern_node is not None and ch is pattern_node:
                continue
            if ch.type == "statements":
                body = self._visit_stmts(ch)
            elif (
                iter_ is not None
                and isinstance(iter_, IRName)
                and iter_.id == "<unknown>"
            ):
                # First non-pattern named child that isn't statements is the iter
                if ch.type != "statements":
                    iter_ = self._visit_expr(ch)

        return IRFor(target=target, iter=iter_, body=body, loc=self._get_location(node))

    def visit_control_transfer_statement(self, node: Any) -> Optional[Any]:
        """
        return expr / break / continue → IRReturn / IRBreak / IRContinue.

        The control-transfer keyword is the first non-named child token.
        """
        keyword = ""
        for ch in node.children:
            if not ch.is_named:
                keyword = self._get_text(ch)
                break
            else:
                # Named child appeared before a keyword — unusual; treat as return
                break

        if keyword == "return":
            val_node = node.named_children[0] if node.named_children else None
            value = self._visit_expr(val_node) if val_node else None
            return IRReturn(value=value, loc=self._get_location(node))
        if keyword == "break":
            return IRBreak(loc=self._get_location(node))
        if keyword == "continue":
            return IRContinue(loc=self._get_location(node))
        if keyword == "throw":
            # Represent as a return with metadata
            val_node = node.named_children[0] if node.named_children else None
            value = self._visit_expr(val_node) if val_node else None
            ret = IRReturn(value=value, loc=self._get_location(node))
            ret._metadata["kind"] = "throw"  # type: ignore[attr-defined]
            return ret

        # Fallback — try to treat as return
        val_node = node.named_children[0] if node.named_children else None
        if val_node is not None:
            return IRReturn(
                value=self._visit_expr(val_node),
                loc=self._get_location(node),
            )
        return None

    # ------------------------------------------------------------------
    # Closures / lambdas
    # ------------------------------------------------------------------

    def visit_lambda_literal(self, node: Any) -> IRFunctionDef:
        """
        { (a: Int) -> Int in body } → IRFunctionDef(kind="closure").
        """
        params: List[IRParameter] = []
        body: List[IRNode] = []

        for ch in node.named_children:
            if ch.type == "lambda_function_type":
                params = self._collect_lambda_params(ch)
            elif ch.type == "statements":
                body = self._visit_stmts(ch)
            elif ch.type == "lambda_function_type_parameters":
                params = self._collect_lambda_params(ch)

        fn = IRFunctionDef(
            name="<closure>",
            params=params,
            body=body,
            loc=self._get_location(node),
        )
        fn._metadata["kind"] = "closure"  # type: ignore[attr-defined]
        return fn

    def _collect_lambda_params(self, node: Any) -> List[IRParameter]:
        """Parse lambda_function_type or lambda_function_type_parameters."""
        params: List[IRParameter] = []
        target = node
        # lambda_function_type may have lambda_function_type_parameters as child
        for ch in node.named_children:
            if ch.type == "lambda_function_type_parameters":
                target = ch
                break

        seen_types: List[str] = []
        for ch in target.named_children:
            if ch.type == "simple_identifier":
                seen_types.append(self._get_text(ch))
            elif ch.type == "user_type":
                # Each identifier before a type annotation is a param name
                pass

        # Simple heuristic: odd-indexed are names (name: Type pairs)
        # lambda_function_type_parameters children alternate name, type
        children_list = [
            c for c in target.named_children if c.type == "simple_identifier"
        ]
        for ch in children_list:
            params.append(
                IRParameter(
                    name=self._get_text(ch),
                    loc=self._get_location(ch),
                )
            )
        return params

    # ------------------------------------------------------------------
    # Expressions
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
        return IRName(id=self._get_text(node), loc=self._get_location(node))

    def visit_simple_identifier(self, node: Any) -> IRName:
        return IRName(id=self._get_text(node), loc=self._get_location(node))

    def visit_identifier(self, node: Any) -> IRName:
        """Dotted identifier (import path etc.) → IRName."""
        # May have simple_identifier children
        parts = [self._get_text(ch) for ch in node.named_children if ch.is_named]
        name = ".".join(parts) if parts else self._get_text(node)
        return IRName(id=name, loc=self._get_location(node))

    def visit_type_identifier(self, node: Any) -> IRName:
        return IRName(id=self._get_text(node), loc=self._get_location(node))

    # Literals
    def visit_integer_literal(self, node: Any) -> IRConstant:
        try:
            raw = self._get_text(node).replace("_", "")
            if raw.startswith(("0x", "0X")):
                val: Any = int(raw, 16)
            elif raw.startswith(("0b", "0B")):
                val = int(raw, 2)
            elif raw.startswith(("0o", "0O")):
                val = int(raw, 8)
            else:
                val = int(raw)
        except ValueError:
            val = self._get_text(node)
        return IRConstant(value=val, loc=self._get_location(node))

    def visit_real_literal(self, node: Any) -> IRConstant:
        try:
            val: Any = float(self._get_text(node).replace("_", ""))
        except ValueError:
            val = self._get_text(node)
        return IRConstant(value=val, loc=self._get_location(node))

    def visit_boolean_literal(self, node: Any) -> IRConstant:
        text = self._get_text(node)
        return IRConstant(value=(text == "true"), loc=self._get_location(node))

    def visit_nil(self, node: Any) -> IRConstant:
        return IRConstant(value=None, loc=self._get_location(node))

    def visit_line_string_literal(self, node: Any) -> IRConstant:
        return IRConstant(value=self._get_text(node), loc=self._get_location(node))

    def visit_multi_line_string_literal(self, node: Any) -> IRConstant:
        return IRConstant(value=self._get_text(node), loc=self._get_location(node))

    def visit_raw_string_literal(self, node: Any) -> IRConstant:
        return IRConstant(value=self._get_text(node), loc=self._get_location(node))

    # Binary / comparison expressions
    def visit_comparison_expression(self, node: Any) -> IRCompare:
        """x < y, x == y, etc. → IRCompare."""
        named = node.named_children
        if len(named) < 2:
            return IRCompare(
                left=IRConstant(value=None, loc=None),
                ops=[CompareOperator.EQ],
                comparators=[],
                loc=self._get_location(node),
            )
        left = self._visit_expr(named[0])
        right = self._visit_expr(named[-1])
        op_text = ""
        for ch in node.children:
            if not ch.is_named:
                t = self._get_text(ch)
                if t in _COMPARE_MAP:
                    op_text = t
                    break
        op = _COMPARE_MAP.get(op_text, CompareOperator.EQ)
        return IRCompare(
            left=left, ops=[op], comparators=[right], loc=self._get_location(node)
        )

    def visit_equality_expression(self, node: Any) -> IRCompare:
        return self.visit_comparison_expression(node)

    def visit_additive_expression(self, node: Any) -> IRExpr:
        """x + y, x - y → IRBinaryOp."""
        return self._binary_op(node)

    def visit_multiplicative_expression(self, node: Any) -> IRExpr:
        return self._binary_op(node)

    def visit_infix_expression(self, node: Any) -> IRExpr:
        """Generic infix expression — dispatch by operator."""
        return self._binary_op(node)

    def visit_conjunction_expression(self, node: Any) -> IRBoolOp:
        """x && y → IRBoolOp(AND)."""
        return self._bool_op(node, BoolOperator.AND)

    def visit_disjunction_expression(self, node: Any) -> IRBoolOp:
        """x || y → IRBoolOp(OR)."""
        return self._bool_op(node, BoolOperator.OR)

    def visit_prefix_expression(self, node: Any) -> IRExpr:
        """!x, -x, etc. — return the operand."""
        for ch in node.named_children:
            return self._visit_expr(ch)
        return IRConstant(value=None, loc=None)

    def _binary_op(self, node: Any) -> IRExpr:
        named = node.named_children
        if len(named) < 2:
            return IRName(id=self._get_text(node), loc=self._get_location(node))
        left = self._visit_expr(named[0])
        right = self._visit_expr(named[-1])
        op_text = ""
        for ch in node.children:
            if not ch.is_named:
                t = self._get_text(ch)
                if t in _BINOP_MAP or t in _COMPARE_MAP:
                    op_text = t
                    break
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

    def _bool_op(self, node: Any, op: BoolOperator) -> IRBoolOp:
        values = [self._visit_expr(ch) for ch in node.named_children]
        return IRBoolOp(op=op, values=values, loc=self._get_location(node))

    # ------------------------------------------------------------------
    # Function calls
    # ------------------------------------------------------------------

    def visit_call_expression(self, node: Any) -> IRCall:
        """
        print(x) / nums.filter { ... } → IRCall.

        The function reference is the first named child; arguments come from
        call_suffix → value_arguments.
        """
        named = node.named_children
        if not named:
            return IRCall(
                func=IRName(id="<unknown>", loc=self._get_location(node)),
                args=[],
                kwargs={},
                loc=self._get_location(node),
            )

        func_node = named[0]
        func_name: str
        if func_node.type == "navigation_expression":
            func_name = self._get_text(func_node).replace("\n", " ")
        else:
            func_name = self._get_text(func_node)

        args: List[IRExpr] = []
        for ch in named[1:]:
            if ch.type == "call_suffix":
                args.extend(self._collect_call_args(ch))

        return IRCall(
            func=IRName(id=func_name, loc=self._get_location(func_node)),
            args=args,
            kwargs={},
            loc=self._get_location(node),
        )

    def _collect_call_args(self, suffix_node: Any) -> List[IRExpr]:
        """Extract argument expressions from a call_suffix node."""
        args: List[IRExpr] = []
        for ch in suffix_node.named_children:
            if ch.type in {"value_arguments", "call_suffix"}:
                for arg in ch.named_children:
                    if arg.type not in {"(", ")", ","}:
                        args.append(self._visit_expr(arg))
            elif ch.type == "lambda_literal":
                args.append(self._visit_expr(ch))
            elif ch.type not in {"(", ")", ","}:
                args.append(self._visit_expr(ch))
        return args

    # ------------------------------------------------------------------
    # Navigation / member access
    # ------------------------------------------------------------------

    def visit_navigation_expression(self, node: Any) -> IRName:
        """foo.bar.baz → IRName("foo.bar.baz")."""
        return IRName(id=self._get_text(node), loc=self._get_location(node))

    # ------------------------------------------------------------------
    # Self
    # ------------------------------------------------------------------

    def visit_self_expression(self, node: Any) -> IRName:
        return IRName(id="self", loc=self._get_location(node))

    # ------------------------------------------------------------------
    # Pattern nodes (often appear as expression fallback)
    # ------------------------------------------------------------------

    def visit_pattern(self, node: Any) -> IRExpr:
        """pattern wrapper → visit inner named child."""
        for ch in node.named_children:
            return self._visit_expr(ch)
        return IRName(id=self._get_text(node), loc=self._get_location(node))

    def visit_directly_assignable_expression(self, node: Any) -> IRExpr:
        """LHS of assignment → visit inner expression."""
        for ch in node.named_children:
            return self._visit_expr(ch)
        return IRName(id=self._get_text(node), loc=self._get_location(node))

    # ------------------------------------------------------------------
    # Enum entries (skipped at top-level)
    # ------------------------------------------------------------------

    def visit_enum_entry(self, node: Any) -> None:
        """enum case north → skip (not representable as standard IR node)."""
        return None

    # ------------------------------------------------------------------
    # Wrapping helpers (unused nodes that would pollute body)
    # ------------------------------------------------------------------

    def visit_multiline_comment(self, node: Any) -> None:
        return None

    def visit_comment(self, node: Any) -> None:
        return None

    def visit_multiline_string_literal(self, node: Any) -> IRConstant:
        return IRConstant(value=self._get_text(node), loc=self._get_location(node))


# ---------------------------------------------------------------------------
# Normalizer
# ---------------------------------------------------------------------------


class SwiftNormalizer(BaseNormalizer):
    """
    Normalizer for Swift source code.

    [20260304_FEATURE] Converts tree-sitter Swift CST to Unified IR.
    Supports Swift 5.x — classes, structs, enums, protocols, actors,
    functions, closures, properties, control flow, and imports.

    Usage::

        from code_scalpel.ir.normalizers.swift_normalizer import SwiftNormalizer

        n = SwiftNormalizer()
        module = n.normalize('func hello() { print("hi") }')
    """

    @property
    def language(self) -> str:
        """[20260304_FEATURE] Language identifier for Swift normalizer."""
        return "swift"

    def normalize(self, source: str, filename: str = "<string>") -> IRModule:
        """Parse Swift source and return an IRModule."""
        language = Language(tree_sitter_swift.language())
        parser = Parser(language)
        tree = parser.parse(bytes(source, "utf-8"))
        visitor = SwiftVisitor(source=source)
        module = visitor.visit(tree.root_node)
        if module is None:
            return IRModule(body=[], source_language="swift")
        cast_module: IRModule = module  # type: ignore[assignment]
        cast_module._metadata["source_file"] = filename
        return cast_module

    def normalize_node(self, node: Any) -> None:
        """[20260304_FEATURE] Node-level dispatch handled by visitor traversal."""
        return None
