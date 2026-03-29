"""
PHP Normalizer - Converts PHP CST (tree-sitter-php) to Unified IR.

[20260303_FEATURE] PHP language support for surgical extraction and analysis.

Key Mappings:
    program                   -> IRModule
    php_tag                   -> (skipped — the <?php marker)
    namespace_definition      -> (records namespace on module metadata, no IR node)
    namespace_use_declaration -> IRImport  (use App\\Foo; / use App\\Foo as Bar;)
    function_definition       -> IRFunctionDef
    class_declaration         -> IRClassDef
    interface_declaration     -> IRClassDef  (bases populated from extends/implements)
    trait_declaration         -> IRClassDef
    method_declaration        -> IRFunctionDef  (inside class/interface/trait bodies)
    property_declaration      -> IRAssign  (class property)
    expression_statement      -> IRExprStmt
    assignment_expression     -> IRAssign
    augmented_assignment_expression -> IRAugAssign
    return_statement          -> IRReturn
    if_statement              -> IRIf
    for_statement             -> IRFor  (C-style; init expression → target)
    foreach_statement         -> IRFor  (foreach $arr as [$k =>] $v)
    while_statement           -> IRWhile
    do_statement              -> IRWhile  (do-while; body visited first)
    function_call_expression  -> IRCall
    scoped_call_expression    -> IRCall  (Foo::bar())
    member_call_expression    -> IRCall  ($obj->bar())
    object_creation_expression -> IRCall  (new Foo(...))
    binary_expression         -> IRBinaryOp (or IRConstant for string concat)
    unary_op_expression       -> (returns operand — no IRUnary in base IR)
    variable_name             -> IRName
    name / qualified_name     -> IRName (class/function identifier)
    integer / float           -> IRConstant
    string / encapsed_string / heredoc -> IRConstant
    boolean / null            -> IRConstant
    echo_statement            -> IRExprStmt(IRCall("echo", args))
    break_statement           -> IRBreak
    continue_statement        -> IRContinue
    formal_parameters         -> list[IRParameter]
    compound_statement        -> list of statements  (block body)

Tree-sitter field names used:
    function_definition:  name, formal_parameters, return_type?, body
    class_declaration:    name, base_clause?, class_implements?, declaration_list
    method_declaration:   [modifiers], name, formal_parameters, return_type?, body
    namespace_definition: name (namespace_name)
    namespace_use_clause: [qualified_name], [alias name]
    assignment_expression: (binary children: left, right)
    for_statement:        (child list includes init, condition, update, body)
    foreach_statement:    [iterable], [key], [value], body
    if_statement:         condition, body, [else_clause | elseif_clause]
    while_statement:      condition, body
    function_call_expression: function, arguments
    member_call_expression:   object, name, arguments
    scoped_call_expression:   scope, name, arguments
    binary_expression:        left, operator, right
    simple_parameter:         [type], variable_name, [default_value]

PHP version: 7.x / 8.x grammar (tree-sitter-php 0.24+)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, cast

import tree_sitter_php
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

# [20260303_BUGFIX] Split into three maps to match IR node types:
# IRBinaryOp (arithmetic/bitwise), IRCompare (comparisons), IRBoolOp (logical)
_BINOP_MAP: Dict[str, BinaryOperator] = {
    "+": BinaryOperator.ADD,
    "-": BinaryOperator.SUB,
    "*": BinaryOperator.MUL,
    "/": BinaryOperator.DIV,
    "%": BinaryOperator.MOD,
    ".": BinaryOperator.ADD,  # PHP string concat — closest IR approximation
    "&": BinaryOperator.BIT_AND,
    "|": BinaryOperator.BIT_OR,
    "^": BinaryOperator.BIT_XOR,
    "<<": BinaryOperator.LSHIFT,
    ">>": BinaryOperator.RSHIFT,
}

_COMPARE_MAP: Dict[str, CompareOperator] = {
    "==": CompareOperator.EQ,
    "!=": CompareOperator.NE,
    "<>": CompareOperator.NE,
    "<": CompareOperator.LT,
    "<=": CompareOperator.LE,
    ">": CompareOperator.GT,
    ">=": CompareOperator.GE,
    "===": CompareOperator.STRICT_EQ,
    "!==": CompareOperator.STRICT_NE,
    "<=>": CompareOperator.EQ,  # PHP spaceship — closest approximation
}

_BOOLOP_MAP: Dict[str, BoolOperator] = {
    "&&": BoolOperator.AND,
    "||": BoolOperator.OR,
    "and": BoolOperator.AND,
    "or": BoolOperator.OR,
    # PHP `xor` has no BoolOperator equivalent — falls through to IRBinaryOp.BIT_XOR
    "xor": BoolOperator.OR,  # best-effort mapping
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
    ".=": AugAssignOperator.ADD,  # PHP concat-assign
}

# ---------------------------------------------------------------------------
# Visitor
# ---------------------------------------------------------------------------


class PHPVisitor(TreeSitterVisitor):
    """Visitor that converts tree-sitter PHP CST nodes to Unified IR."""

    @property
    def language(self) -> str:
        return "php"

    def __init__(self, source: str = "") -> None:
        super().__init__()
        self.ctx.source = source
        self._namespace: str = ""  # current PHP namespace

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
    # Module
    # ------------------------------------------------------------------

    def visit_program(self, node: Any) -> IRModule:
        """Top-level PHP program → IRModule."""
        module = IRModule(
            body=[],
            source_language="php",
            loc=self._get_location(node),
        )
        for child in node.named_children:
            if child.type == "php_tag":
                continue  # skip the <?php tag
            result = self.visit(child)
            if result is None:
                continue
            elif isinstance(result, list):
                module.body.extend(result)
            elif isinstance(result, IRNode):
                module.body.append(result)
        return module

    # ------------------------------------------------------------------
    # Namespace & Imports
    # ------------------------------------------------------------------

    def visit_namespace_definition(self, node: Any) -> None:
        """Record namespace on visitor; produce no IR node."""
        name_node = node.child_by_field_name("name")
        if name_node is not None:
            self._namespace = self._get_text(name_node).replace("\\", ".")
        return None

    def visit_namespace_use_declaration(self, node: Any) -> List[IRImport]:
        """
        PHP `use` statement → one IRImport per clause.

        Examples:
            use App\\Models\\User;
            use App\\Services\\Auth as AuthService;
            use App\\Helpers\\{Str, Arr};
        """
        imports: List[IRImport] = []
        for child in node.named_children:
            if child.type == "namespace_use_clause":
                imp = self._visit_use_clause(child)
                if imp is not None:
                    imports.append(imp)
            elif child.type == "namespace_use_group":
                # use App\Helpers\{Str, Arr}
                for sub in child.named_children:
                    if sub.type == "namespace_use_clause":
                        imp = self._visit_use_clause(sub)
                        if imp is not None:
                            imports.append(imp)
        return imports

    def _visit_use_clause(self, node: Any) -> Optional[IRImport]:
        """Parse a single namespace_use_clause into IRImport."""
        parts: List[str] = []
        alias: Optional[str] = None
        for child in node.named_children:
            if child.type == "qualified_name":
                parts.append(self._qualified_name_text(child))
            elif child.type == "name" and parts:
                # The trailing `as Alias` — last bare name child is alias
                alias = self._get_text(child)
        if not parts:
            return None
        module_path = parts[0]
        # Last component is the imported name; everything before is the module
        segments = module_path.rsplit(".", 1)
        module = segments[0] if len(segments) > 1 else ""
        name = segments[-1]
        return IRImport(
            module=module,
            names=[name],
            alias=alias,
            loc=self._get_location(node),
        )

    def _qualified_name_text(self, node: Any) -> str:
        """Flatten qualified_name to dotted string (App\\Foo\\Bar → App.Foo.Bar)."""
        return self._get_text(node).replace("\\", ".")

    # ------------------------------------------------------------------
    # Function definitions
    # ------------------------------------------------------------------

    def visit_function_definition(self, node: Any) -> IRFunctionDef:
        """Top-level PHP function → IRFunctionDef."""
        name_node = node.child_by_field_name("name")
        name = self._get_text(name_node) if name_node else "<anon>"

        params = self._visit_formal_parameters(
            node.child_by_field_name("parameters")
            or node.child_by_field_name("formal_parameters")
        )

        ret_node = node.child_by_field_name("return_type")
        return_type = self._get_text(ret_node) if ret_node else None

        body_node = node.child_by_field_name("body")
        body = self._visit_compound(body_node) if body_node else []

        return IRFunctionDef(
            name=name,
            params=params,
            body=body,
            return_type=return_type,
            loc=self._get_location(node),
        )

    # ------------------------------------------------------------------
    # Class / interface / trait
    # ------------------------------------------------------------------

    def visit_class_declaration(self, node: Any) -> IRClassDef:
        """PHP class → IRClassDef."""
        return self._visit_class_like(node)

    def visit_interface_declaration(self, node: Any) -> IRClassDef:
        """PHP interface → IRClassDef."""
        return self._visit_class_like(node)

    def visit_trait_declaration(self, node: Any) -> IRClassDef:
        """PHP trait → IRClassDef."""
        return self._visit_class_like(node)

    def _visit_class_like(self, node: Any) -> IRClassDef:
        name_node = node.child_by_field_name("name")
        name = self._get_text(name_node) if name_node else "<anon>"

        bases: List[IRExpr] = []
        base_node = node.child_by_field_name("base_clause")
        if base_node is not None:
            for child in base_node.named_children:
                if child.type == "name":
                    bases.append(
                        IRName(id=self._get_text(child), loc=self._get_location(child))
                    )

        impl_node = node.child_by_field_name("class_implements")
        if impl_node is not None:
            for child in impl_node.named_children:
                if child.type == "name":
                    bases.append(
                        IRName(id=self._get_text(child), loc=self._get_location(child))
                    )

        decl_node = node.child_by_field_name("body")
        if decl_node is None:
            # tree-sitter-php uses declaration_list
            for child in node.named_children:
                if child.type == "declaration_list":
                    decl_node = child
                    break

        body = self._visit_declaration_list(decl_node) if decl_node else []

        return IRClassDef(
            name=name,
            bases=bases,
            body=body,
            loc=self._get_location(node),
        )

    def _visit_declaration_list(self, node: Any) -> List[IRNode]:
        """Visit class body (declaration_list)."""
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

    def visit_method_declaration(self, node: Any) -> IRFunctionDef:
        """Class/interface method → IRFunctionDef."""
        name_node = node.child_by_field_name("name")
        name = self._get_text(name_node) if name_node else "<anon>"

        params = self._visit_formal_parameters(
            node.child_by_field_name("parameters")
            or node.child_by_field_name("formal_parameters")
        )

        ret_node = node.child_by_field_name("return_type")
        return_type = self._get_text(ret_node) if ret_node else None

        body_node = node.child_by_field_name("body")
        body = self._visit_compound(body_node) if body_node else []

        return IRFunctionDef(
            name=name,
            params=params,
            body=body,
            return_type=return_type,
            loc=self._get_location(node),
        )

    def visit_property_declaration(self, node: Any) -> Optional[IRAssign]:
        """Class property → IRAssign if it has a default value."""
        for child in node.named_children:
            if child.type == "property_element":
                var_node = child.child_by_field_name("name")
                if var_node is None:
                    # named children: first is variable_name
                    for c in child.named_children:
                        if c.type == "variable_name":
                            var_node = c
                            break
                if var_node is None:
                    continue
                var_name = self._visit_variable_or_name(var_node)
                val_node = child.child_by_field_name("default_value")
                if val_node is not None:
                    value = cast(IRExpr, self.visit(val_node))
                else:
                    value = IRConstant(value=None, loc=self._get_location(child))
                return IRAssign(
                    targets=[var_name],
                    value=value,
                    loc=self._get_location(node),
                )
        return None

    # ------------------------------------------------------------------
    # Parameter list helpers
    # ------------------------------------------------------------------

    def _visit_formal_parameters(self, node: Any) -> List[IRParameter]:
        if node is None:
            return []
        params: List[IRParameter] = []
        for child in node.named_children:
            if child.type in (
                "simple_parameter",
                "variadic_parameter",
                "property_promotion_parameter",
            ):
                params.append(self._visit_simple_parameter(child))
        return params

    def _visit_simple_parameter(self, node: Any) -> IRParameter:
        type_annotation: Optional[str] = None
        name = "<param>"
        for child in node.named_children:
            if child.type in (
                "primitive_type",
                "named_type",
                "union_type",
                "nullable_type",
                "intersection_type",
            ):
                type_annotation = self._get_text(child)
            elif child.type == "variable_name":
                name_node = child.child_by_field_name("name")
                if name_node:
                    name = self._get_text(name_node)
                else:
                    name = self._get_text(child).lstrip("$")
            elif child.type == "name":
                # fallback: might be parameter name without $ prefix
                name = self._get_text(child)
        return IRParameter(
            name=name,
            type_annotation=type_annotation,
            loc=self._get_location(node),
        )

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------

    def visit_compound_statement(self, node: Any) -> List[IRNode]:
        return self._visit_compound(node)

    def _visit_compound(self, node: Any) -> List[IRNode]:
        """Visit a compound_statement and return its children as a list."""
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

    def visit_expression_statement(self, node: Any) -> Optional[IRNode]:
        """Wrap expression as IRExprStmt (or return assignment directly)."""
        for child in node.named_children:
            r = self.visit(child)
            if r is None:
                return None
            # Unwrap lists (should be single element for expressions)
            if isinstance(r, list):
                r = r[0] if r else None
                if r is None:
                    continue
            if isinstance(r, (IRAssign, IRAugAssign)):
                return r  # assignments are statements directly
            if isinstance(r, IRExpr):
                return IRExprStmt(value=r, loc=self._get_location(node))
            return r
        return None

    def visit_echo_statement(self, node: Any) -> IRExprStmt:
        """echo $x, $y → IRExprStmt(IRCall('echo', [...]))"""
        args: List[IRExpr] = []
        for child in node.named_children:
            r = self.visit(child)
            if isinstance(r, IRExpr):
                args.append(r)
        return IRExprStmt(
            value=IRCall(
                func=IRName(id="echo", loc=self._get_location(node)),
                args=args,
                loc=self._get_location(node),
            ),
            loc=self._get_location(node),
        )

    def visit_return_statement(self, node: Any) -> IRReturn:
        value: Optional[IRExpr] = None
        for child in node.named_children:
            r = self.visit(child)
            if isinstance(r, IRExpr):
                value = r
                break
        return IRReturn(value=value, loc=self._get_location(node))

    def visit_if_statement(self, node: Any) -> IRIf:
        test: Optional[IRExpr] = None
        body: List[IRNode] = []
        orelse: List[IRNode] = []

        for child in node.named_children:
            if child.type == "parenthesized_expression":
                for sub in child.named_children:
                    r = self.visit(sub)
                    if isinstance(r, IRExpr):
                        test = r
                        break
            elif child.type == "compound_statement":
                body = self._visit_compound(child)
            elif child.type == "else_clause":
                orelse = self._visit_else_clause(child)
            elif child.type == "elseif_clause":
                orelse = [self._visit_elseif_clause(child)]

        return IRIf(test=test, body=body, orelse=orelse, loc=self._get_location(node))

    def _visit_else_clause(self, node: Any) -> List[IRNode]:
        for child in node.named_children:
            if child.type == "compound_statement":
                return self._visit_compound(child)
            r = self.visit(child)
            if r is None:
                continue
            return [r] if isinstance(r, IRNode) else r  # type: ignore[return-value]
        return []

    def _visit_elseif_clause(self, node: Any) -> IRIf:
        """elseif (...) { ... } → IRIf"""
        test: Optional[IRExpr] = None
        body: List[IRNode] = []
        orelse: List[IRNode] = []
        for child in node.named_children:
            if child.type == "parenthesized_expression":
                for sub in child.named_children:
                    r = self.visit(sub)
                    if isinstance(r, IRExpr):
                        test = r
                        break
            elif child.type == "compound_statement":
                body = self._visit_compound(child)
            elif child.type == "else_clause":
                orelse = self._visit_else_clause(child)
            elif child.type == "elseif_clause":
                orelse = [self._visit_elseif_clause(child)]
        return IRIf(test=test, body=body, orelse=orelse, loc=self._get_location(node))

    def visit_for_statement(self, node: Any) -> IRFor:
        """
        C-style for loop → IRFor.

        PHP tree-sitter for_statement children (named):
            [init_expressions], [condition_expressions], [update_expressions], body
        We store the first init expression as `target` and first condition as `iter`.
        """
        target: Optional[IRExpr] = None
        iter_expr: Optional[IRExpr] = None
        body: List[IRNode] = []

        # PHP for_statement uses specific child order: init, cond, update, body
        # We iterate children and resolve by type
        named = [c for c in node.named_children]
        # Last named child should be compound_statement (body) or single statement
        if named and named[-1].type == "compound_statement":
            body = self._visit_compound(named[-1])
            named = named[:-1]

        # Remaining children (in order): init, condition, update
        for i, child in enumerate(named):
            r = self.visit(child)
            if i == 0 and isinstance(r, (IRExpr, IRAssign, IRAugAssign)):
                # Store init expression as target
                target = (
                    cast(IRExpr, r)
                    if isinstance(r, IRExpr)
                    else IRName(id="<init>", loc=self._get_location(child))
                )
            elif i == 1 and isinstance(r, IRExpr):
                iter_expr = r

        return IRFor(
            target=target, iter=iter_expr, body=body, loc=self._get_location(node)
        )

    def visit_foreach_statement(self, node: Any) -> IRFor:
        """
        foreach ($arr as $val) / foreach ($arr as $key => $val) → IRFor.
        """
        iterable: Optional[IRExpr] = None
        target: Optional[IRExpr] = None
        body: List[IRNode] = []

        named = node.named_children
        # Children: iterable_expr, [key_expr], value_expr, [body]
        # They may be separated by `pair` node for key => value
        for child in named:
            if child.type == "compound_statement":
                body = self._visit_compound(child)
            elif child.type == "pair":
                # key => value: $key => $val
                children = child.named_children
                if children:
                    val_node = children[-1]
                    r = self.visit(val_node)
                    if isinstance(r, IRExpr):
                        target = r
            elif child.type == "variable_name":
                if iterable is None:
                    iterable = self._visit_variable_or_name(child)
                else:
                    target = self._visit_variable_or_name(child)
            else:
                r = self.visit(child)
                if isinstance(r, IRExpr):
                    if iterable is None:
                        iterable = r
                    elif target is None:
                        target = r

        return IRFor(
            target=target,
            iter=iterable,
            body=body,
            is_for_in=True,
            loc=self._get_location(node),
        )

    def visit_while_statement(self, node: Any) -> IRWhile:
        test: Optional[IRExpr] = None
        body: List[IRNode] = []

        for child in node.named_children:
            if child.type == "parenthesized_expression":
                for sub in child.named_children:
                    r = self.visit(sub)
                    if isinstance(r, IRExpr):
                        test = r
                        break
            elif child.type == "compound_statement":
                body = self._visit_compound(child)
            else:
                # single-statement (no-brace) while body
                r = self.visit(child)
                if isinstance(r, IRNode) and not isinstance(r, IRExpr):
                    body = [r]

        return IRWhile(test=test, body=body, loc=self._get_location(node))

    def visit_do_statement(self, node: Any) -> IRWhile:
        """do { ... } while (cond) → IRWhile (body-first; same IR shape)."""
        test: Optional[IRExpr] = None
        body: List[IRNode] = []

        for child in node.named_children:
            if child.type == "compound_statement":
                body = self._visit_compound(child)
            elif child.type == "parenthesized_expression":
                for sub in child.named_children:
                    r = self.visit(sub)
                    if isinstance(r, IRExpr):
                        test = r
                        break

        return IRWhile(test=test, body=body, loc=self._get_location(node))

    def visit_break_statement(self, _: Any) -> IRBreak:
        return IRBreak()

    def visit_continue_statement(self, _: Any) -> IRContinue:
        return IRContinue()

    # ------------------------------------------------------------------
    # Assignments
    # ------------------------------------------------------------------

    def visit_assignment_expression(self, node: Any) -> IRAssign:
        children = node.named_children
        if len(children) >= 2:
            lhs = cast(IRExpr, self.visit(children[0]))
            rhs = cast(IRExpr, self.visit(children[1]))
        else:
            lhs = IRName(id="<lhs>", loc=self._get_location(node))
            rhs = IRConstant(value=None, loc=self._get_location(node))
        return IRAssign(
            targets=[lhs],
            value=rhs,
            loc=self._get_location(node),
        )

    def visit_augmented_assignment_expression(self, node: Any) -> IRAugAssign:
        """$x += 1 → IRAugAssign."""
        children = node.named_children
        target: Optional[IRExpr] = None
        value: Optional[IRExpr] = None
        if len(children) >= 2:
            target = cast(IRExpr, self.visit(children[0]))
            value = cast(IRExpr, self.visit(children[1]))

        # Operator is an anonymous child: find it between lhs and rhs
        op_text = ""
        for child in node.children:
            if not child.is_named and child.type not in ("(", ")", "{", "}"):
                op_text = self._get_text(child)
                break

        op = _AUG_ASSIGN_MAP.get(op_text, AugAssignOperator.ADD)
        return IRAugAssign(
            target=target, op=op, value=value, loc=self._get_location(node)
        )

    # ------------------------------------------------------------------
    # Expressions
    # ------------------------------------------------------------------

    def visit_binary_expression(self, node: Any) -> IRNode:
        """PHP binary expression → IRBinaryOp / IRCompare / IRBoolOp."""
        children = node.named_children
        if len(children) < 2:
            return IRConstant(value=self._get_text(node), loc=self._get_location(node))

        lhs = cast(IRExpr, self.visit(children[0]))
        rhs = cast(IRExpr, self.visit(children[1]))

        # Operator is an anonymous child — find it
        op_text = ""
        for child in node.children:
            if not child.is_named:
                text = self._get_text(child).strip()
                if text and text not in ("(", ")"):
                    op_text = text
                    break

        # [20260303_BUGFIX] Dispatch to the correct IR node type by operator category
        cmp_op = _COMPARE_MAP.get(op_text)
        if cmp_op is not None:
            return IRCompare(
                left=lhs,
                ops=[cmp_op],
                comparators=[rhs],
                loc=self._get_location(node),
            )

        bool_op = _BOOLOP_MAP.get(op_text)
        if bool_op is not None:
            return IRBoolOp(op=bool_op, values=[lhs, rhs], loc=self._get_location(node))

        bin_op = _BINOP_MAP.get(op_text)
        if bin_op is not None:
            return IRBinaryOp(
                left=lhs, op=bin_op, right=rhs, loc=self._get_location(node)
            )

        # Unknown operator — collapse to constant
        return IRConstant(value=self._get_text(node), loc=self._get_location(node))

    def visit_function_call_expression(self, node: Any) -> IRCall:
        """greet("world") → IRCall."""
        func_node = node.child_by_field_name("function")
        if func_node is None:
            for child in node.named_children:
                func_node = child
                break
        func: IRExpr = (
            cast(IRExpr, self.visit(func_node))
            if func_node
            else IRName(id="<unknown>", loc=self._get_location(node))
        )
        args = self._visit_arguments(node.child_by_field_name("arguments"))
        return IRCall(func=func, args=args, loc=self._get_location(node))

    def visit_member_call_expression(self, node: Any) -> IRCall:
        """$obj->method(...) → IRCall."""
        obj_node = node.child_by_field_name("object")
        name_node = node.child_by_field_name("name")
        method_name = self._get_text(name_node) if name_node else "<method>"
        obj_text = self._get_text(obj_node).lstrip("$") if obj_node else "<obj>"
        func = IRName(id=f"{obj_text}.{method_name}", loc=self._get_location(node))
        args = self._visit_arguments(node.child_by_field_name("arguments"))
        return IRCall(func=func, args=args, loc=self._get_location(node))

    def visit_scoped_call_expression(self, node: Any) -> IRCall:
        """Foo::bar(...) → IRCall."""
        scope_node = node.child_by_field_name("scope")
        name_node = node.child_by_field_name("name")
        scope = self._get_text(scope_node) if scope_node else "<scope>"
        method = self._get_text(name_node) if name_node else "<name>"
        func = IRName(id=f"{scope}.{method}", loc=self._get_location(node))
        args = self._visit_arguments(node.child_by_field_name("arguments"))
        return IRCall(func=func, args=args, loc=self._get_location(node))

    def visit_object_creation_expression(self, node: Any) -> IRCall:
        """new Foo(...) → IRCall('__new__Foo', ...)."""
        class_node = None
        for child in node.named_children:
            if child.type in ("qualified_name", "name", "variable_name"):
                class_node = child
                break
        class_name = self._get_text(class_node) if class_node else "<class>"
        func = IRName(id=f"__new__{class_name}", loc=self._get_location(node))
        args = self._visit_arguments(node.child_by_field_name("arguments"))
        return IRCall(func=func, args=args, loc=self._get_location(node))

    def _visit_arguments(self, node: Any) -> List[IRExpr]:
        if node is None:
            return []
        args: List[IRExpr] = []
        for child in node.named_children:
            if child.type == "argument":
                for sub in child.named_children:
                    r = self.visit(sub)
                    if isinstance(r, IRExpr):
                        args.append(r)
                        break
            else:
                r = self.visit(child)
                if isinstance(r, IRExpr):
                    args.append(r)
        return args

    def visit_parenthesized_expression(self, node: Any) -> Optional[IRNode]:
        for child in node.named_children:
            result = self.visit(child)
            # Unwrap lists (should be single element for parenthesized expressions)
            if isinstance(result, list):
                return result[0] if result else None
            return result
        return None

    # ------------------------------------------------------------------
    # Atoms / terminals
    # ------------------------------------------------------------------

    def visit_variable_name(self, node: Any) -> IRName:
        """$var → IRName(id='var') — strips leading $ from PHP variable names."""
        name_node = node.child_by_field_name("name")
        if name_node is not None:
            return IRName(id=self._get_text(name_node), loc=self._get_location(node))
        # Fallback: strip $ from raw text
        text = self._get_text(node).lstrip("$")
        return IRName(id=text, loc=self._get_location(node))

    def _visit_variable_or_name(self, node: Any) -> IRName:
        if node.type == "variable_name":
            return self.visit_variable_name(node)
        return IRName(id=self._get_text(node), loc=self._get_location(node))

    def visit_name(self, node: Any) -> IRName:
        return IRName(id=self._get_text(node), loc=self._get_location(node))

    def visit_qualified_name(self, node: Any) -> IRName:
        return IRName(id=self._qualified_name_text(node), loc=self._get_location(node))

    def visit_integer(self, node: Any) -> IRConstant:
        text = self._get_text(node)
        try:
            value: Any = int(text, 0)
        except ValueError:
            value = text
        return IRConstant(value=value, loc=self._get_location(node))

    def visit_float(self, node: Any) -> IRConstant:
        text = self._get_text(node)
        try:
            value: Any = float(text)
        except ValueError:
            value = text
        return IRConstant(value=value, loc=self._get_location(node))

    def visit_string(self, node: Any) -> IRConstant:
        return IRConstant(value=self._get_text(node), loc=self._get_location(node))

    def visit_encapsed_string(self, node: Any) -> IRConstant:
        return IRConstant(value=self._get_text(node), loc=self._get_location(node))

    def visit_heredoc(self, node: Any) -> IRConstant:
        return IRConstant(value=self._get_text(node), loc=self._get_location(node))

    def visit_boolean(self, node: Any) -> IRConstant:
        text = self._get_text(node).lower()
        return IRConstant(value=(text == "true"), loc=self._get_location(node))

    def visit_null(self, node: Any) -> IRConstant:
        return IRConstant(value=None, loc=self._get_location(node))


# ---------------------------------------------------------------------------
# Normalizer (public API)
# ---------------------------------------------------------------------------


class PHPNormalizer(BaseNormalizer):
    """
    Normalize PHP source code to Unified IR.

    [20260303_FEATURE] PHP Phase 1 — tree-sitter-php → IRModule.

    Uses `tree_sitter_php.language_php()` which handles both pure PHP
    and embedded PHP (<?php tags in HTML context).

    Supported file extensions: .php, .php3, .php4, .php5, .php7, .phtml
    """

    @property
    def language(self) -> str:
        return "php"

    _MAX_CACHE: int = 16

    def __init__(self) -> None:
        # [20260303_FEATURE] Instance-level cache (not class-level) — prevents
        # cross-instance contamination, matching the kotlin_normalizer fix.
        self._tree_cache: Dict[int, Any] = {}
        self._ts_language = Language(tree_sitter_php.language_php())  # type: ignore[call-arg]
        self._parser = Parser()
        self._parser.language = self._ts_language
        self._visitor: Optional[PHPVisitor] = None

    def normalize(self, source: str, filename: str = "<string>") -> IRModule:
        """Parse PHP source and return a Unified IRModule."""
        tree = self._parse_cached(source)
        self._visitor = PHPVisitor(source)
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
