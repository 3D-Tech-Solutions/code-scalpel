#!/usr/bin/env python3
"""
Kotlin Normalizer - Converts Kotlin CST (tree-sitter-kotlin) to Unified IR.

[20260303_FEATURE] Kotlin language support for surgical extraction and analysis.

Key Mappings:
    source_file               -> IRModule
    package_header            -> (records package name on module metadata)
    import                    -> IRImport (single or starred)
    function_declaration      -> IRFunctionDef (regular + extension functions)
    class_declaration         -> IRClassDef (class, data class, interface)
    object_declaration        -> IRClassDef (kind="object")
    companion_object          -> IRClassDef (kind="companion_object")
    property_declaration      -> IRAssign   (val / var at file/class scope)
    assignment                -> IRAssign   (re-assignment)
    return_expression         -> IRReturn
    if_expression             -> IRIf
    when_expression           -> IRIf  (simplified — each branch becomes a stub)
    for_statement             -> IRFor
    while_statement           -> IRFor  (kind="while")
    call_expression           -> IRCall
    lambda_literal            -> IRFunctionDef (kind="lambda")
    binary_expression         -> IRBinaryOp
    infix_expression          -> IRBinaryOp (operator name stored in metadata)
    break_expression          -> IRBreak
    continue_expression       -> IRContinue
    identifier                -> IRName
    number_literal / string_literal / boolean_literal / null -> IRConstant

Tree-sitter field names used:
    function_declaration:  user_type (receiver), identifier (name),
                           function_value_parameters, user_type (return), function_body
    class_declaration:     identifier (name), primary_constructor, class_body
    companion_object:      identifier? (name), class_body
    property_declaration:  variable_declaration (name + type), expression (value)
    if_expression:         condition, block (consequence), else (alternative)
    for_statement:         variable_declaration (loop var), expression (iterable), block
    while_statement:       expression (condition), block
    call_expression:       qualified_identifier / navigation_expression (func), value_arguments
    lambda_literal:        lambda_parameters, statements (body)
    binary_expression:     children: left, operator, right
    parameter:             identifier (name), user_type (type)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, cast

import tree_sitter_kotlin
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
    "and": BinaryOperator.BIT_AND,  # Kotlin infix 'and'
    "or": BinaryOperator.BIT_OR,  # Kotlin infix 'or'
    "xor": BinaryOperator.BIT_XOR,
    "&&": BinaryOperator.BIT_AND,  # logical AND → closest IR op
    "||": BinaryOperator.BIT_OR,  # logical OR  → closest IR op
    "..": BinaryOperator.ADD,  # range operator fallback
    ".": BinaryOperator.ADD,  # navigation fallback
    # NOTE: comparison operators (==, !=, <, <=, >, >=, is, in) are NOT in
    # BinaryOperator — they fall through to IRConstant (see visit_binary_expression).
}

# ---------------------------------------------------------------------------
# Visitor
# ---------------------------------------------------------------------------


class KotlinVisitor(TreeSitterVisitor):
    """Visitor that converts tree-sitter Kotlin CST nodes to Unified IR."""

    @property
    def language(self) -> str:
        return "kotlin"

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

    def _text_of(self, node: Any) -> str:
        if node is None:
            return ""
        return self._get_text(node)

    def _visit_block(self, block_node: Any) -> List[IRNode]:
        """Visit a `block` or `function_body` node and collect IR nodes."""
        if block_node is None:
            return []
        results: List[IRNode] = []

        # function_body can contain either a `block` or `= expr` (expression body)
        if block_node.type == "function_body":
            for child in block_node.named_children:
                if child.type == "block":
                    return self._visit_block(child)
                # expression body: `= expr`
                res = self.visit(child)
                if res is None:
                    continue
                if isinstance(res, list):
                    results.extend(r for r in res if r is not None)
                else:
                    ret = IRReturn(
                        value=cast(Any, res),
                        loc=self._get_location(child),
                        source_language=self.language,
                    )
                    results.append(ret)
            return results

        # Regular block: { statements... }
        # Note: named_children never include "{" or "}" — they are unnamed tokens.
        for child in block_node.named_children:
            res = self.visit(child)
            if res is None:
                continue
            if isinstance(res, list):
                results.extend(r for r in res if r is not None)
            else:
                results.append(cast(IRNode, res))
        return results

    def _visit_statements(self, node: Any) -> List[IRNode]:
        """Visit all named children collecting IR nodes."""
        results: List[IRNode] = []
        for child in node.named_children:
            res = self.visit(child)
            if res is None:
                continue
            if isinstance(res, list):
                results.extend(r for r in res if r is not None)
            else:
                results.append(cast(IRNode, res))
        return results

    def _parse_function_value_parameters(self, params_node: Any) -> List[IRParameter]:
        """Parse Kotlin function_value_parameters: `(a: Int, b: String = "x")`."""
        if params_node is None:
            return []
        params: List[IRParameter] = []
        for child in params_node.named_children:
            if child.type == "parameter":
                # parameter: identifier ":" user_type ["=" default_value]
                name_nodes = [c for c in child.named_children if c.type == "identifier"]
                type_nodes = [
                    c
                    for c in child.named_children
                    if c.type
                    in ("user_type", "nullable_type", "function_type", "dynamic")
                ]
                name = self._text_of(name_nodes[0]) if name_nodes else ""
                type_ann = self._text_of(type_nodes[0]) if type_nodes else None
                params.append(IRParameter(name=name, type_annotation=type_ann))
            elif child.type == "multi_variable_declaration":
                # Destructured parameter like (a, b)
                for nc in child.named_children:
                    if nc.type == "variable_declaration":
                        n = next(
                            (c for c in nc.named_children if c.type == "identifier"),
                            None,
                        )
                        params.append(IRParameter(name=self._text_of(n) if n else ""))
        return params

    def _get_identifier_name(self, node: Any) -> str:
        """Extract the simple identifier name from a node."""
        for child in node.named_children:
            if child.type == "identifier":
                return self._text_of(child)
        if node.type == "identifier":
            return self._text_of(node)
        return self._text_of(node)

    def _parse_class_body(self, body_node: Any) -> List[IRNode]:
        """Visit a `class_body` and return IR nodes."""
        if body_node is None:
            return []
        results: List[IRNode] = []
        for child in body_node.named_children:
            res = self.visit(child)
            if res is None:
                continue
            if isinstance(res, list):
                results.extend(r for r in res if r is not None)
            else:
                results.append(cast(IRNode, res))
        return results

    # ------------------------------------------------------------------
    # Root
    # ------------------------------------------------------------------

    def visit_source_file(self, node: Any) -> IRModule:
        """Root node of a Kotlin file."""
        body: List[IRNode] = []
        module = IRModule(body=body, source_language=self.language)
        for child in node.named_children:
            if child.type == "package_header":
                # Extract package name from qualified_identifier
                qi = next(
                    (
                        c
                        for c in child.named_children
                        if c.type == "qualified_identifier"
                    ),
                    None,
                )
                if qi:
                    module._metadata["package"] = self._text_of(qi)
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

    def visit_import(self, node: Any) -> Optional[IRImport]:
        """import kotlin.io.println  /  import java.util.*"""
        qi = next(
            (c for c in node.named_children if c.type == "qualified_identifier"), None
        )
        if qi is None:
            return None
        # Check for star import: next sibling after qi is "*"
        raw_text = self._text_of(node)
        is_star = raw_text.rstrip().endswith("*")
        # Build module path from qualified_identifier
        module_path = self._text_of(qi)
        if is_star and not module_path.endswith("*"):
            module_path = module_path.rstrip(".")
        return IRImport(
            module=module_path,
            names=[],
            alias=None,
            is_star=is_star,
            loc=self._get_location(node),
            source_language=self.language,
        )

    # ------------------------------------------------------------------
    # Functions
    # ------------------------------------------------------------------

    def visit_function_declaration(self, node: Any) -> IRFunctionDef:
        """
        fun greet(name: String): String { return "Hello $name" }
        fun String.shout(): String = this.uppercase()  (extension function)
        """
        # Detect extension function: user_type before "." before identifier
        # Pattern: fun <user_type> . <identifier> ...
        receiver: Optional[str] = None
        name: str = "unknown"
        func_name_idx = -1

        # Walk named children to find receiver + name
        named = node.named_children
        for i, c in enumerate(named):
            if c.type in ("simple_identifier", "identifier"):
                # [20260303_BUGFIX] removed dead `elif c.type == "identifier"` branch
                if i > 0 and named[i - 1].type == "user_type":
                    receiver = self._text_of(named[i - 1])
                name = self._text_of(c)
                func_name_idx = i
                break

        # Fallback: first identifier in named children
        if func_name_idx == -1:
            for c in named:
                if c.type == "identifier":
                    name = self._text_of(c)
                    break

        # Parameters
        params_node = next(
            (c for c in named if c.type == "function_value_parameters"), None
        )
        params = self._parse_function_value_parameters(params_node)

        # Return type: user_type / nullable_type AFTER the parameter list
        return_type: Optional[str] = None
        if params_node is not None:
            after_params = False
            for c in named:
                if c is params_node:
                    after_params = True
                    continue
                if after_params and c.type in (
                    "user_type",
                    "nullable_type",
                    "function_type",
                    "dynamic",
                ):
                    return_type = self._text_of(c)
                    break

        # Body
        body_node = next(
            (c for c in named if c.type in ("function_body", "block")), None
        )
        body = self._visit_block(body_node)

        fn = IRFunctionDef(
            name=name,
            params=params,
            body=body,
            return_type=return_type,
            source_language=self.language,
            loc=self._get_location(node),
        )
        if receiver:
            fn._metadata["receiver"] = receiver
            fn._metadata["kind"] = "extension"
        return fn

    def visit_lambda_literal(self, node: Any) -> IRFunctionDef:
        """{ a: Int, b: Int -> a + b }"""
        # lambda_parameters node
        params_raw = next(
            (c for c in node.named_children if c.type == "lambda_parameters"), None
        )
        params: List[IRParameter] = []
        if params_raw:
            for p in params_raw.named_children:
                if p.type == "lambda_parameter":
                    names = [c for c in p.named_children if c.type == "identifier"]
                    types = [
                        c
                        for c in p.named_children
                        if c.type in ("user_type", "nullable_type")
                    ]
                    pname = self._text_of(names[0]) if names else "_"
                    ptype = self._text_of(types[0]) if types else None
                    params.append(IRParameter(name=pname, type_annotation=ptype))

        # Body: statements after "->"
        body: List[IRNode] = []
        in_body = False
        for child in node.named_children:
            if child.type == "lambda_parameters":
                continue
            if child.type in ("->",) or self._text_of(child) == "->":
                in_body = True
                continue
            if in_body:
                res = self.visit(child)
                if res is None:
                    continue
                if isinstance(res, list):
                    body.extend(r for r in res if r is not None)
                else:
                    body.append(cast(IRNode, res))

        # If no explicit arrow, whole body is the expression
        if not in_body:
            for child in node.named_children:
                if child.type not in ("lambda_parameters", "{", "}"):
                    res = self.visit(child)
                    if res is not None:
                        if isinstance(res, list):
                            body.extend(r for r in res if r is not None)
                        else:
                            body.append(cast(IRNode, res))

        fn = IRFunctionDef(
            name="<lambda>",
            params=params,
            body=body,
            return_type=None,
            source_language=self.language,
            loc=self._get_location(node),
        )
        fn._metadata["kind"] = "lambda"
        return fn

    # ------------------------------------------------------------------
    # Class declarations
    # ------------------------------------------------------------------

    def visit_class_declaration(self, node: Any) -> IRClassDef:
        """
        class Animal(val name: String) { fun speak() = "..." }
        data class Point(val x: Int, val y: Int)
        interface Drawable { fun draw() }
        """
        # Detect if it's an interface, data class, sealed class, etc.
        is_interface = "interface" in [c.type for c in node.children]

        name_node = next(
            (c for c in node.named_children if c.type == "identifier"), None
        )
        name = self._text_of(name_node) if name_node else "Unknown"

        # Primary constructor parameters → stored in metadata
        primary_ctor = next(
            (c for c in node.named_children if c.type == "primary_constructor"), None
        )

        # Base classes
        bases: List[IRExpr] = []
        supers = [
            c
            for c in node.named_children
            if c.type
            in (
                "delegation_specifier",
                "explicit_delegation",
                "annotated_delegation_specifier",
            )
        ]
        for spec in supers:
            bases.append(IRName(id=self._text_of(spec), loc=self._get_location(spec)))

        # Body
        body_node = next(
            (c for c in node.named_children if c.type == "class_body"), None
        )
        body = self._parse_class_body(body_node) if body_node else []

        cls = IRClassDef(
            name=name,
            bases=bases,
            body=body,
            source_language=self.language,
            loc=self._get_location(node),
        )
        cls._metadata["kind"] = "interface" if is_interface else "class"

        # Store primary constructor parameters
        if primary_ctor:
            params_node = next(
                (
                    c
                    for c in primary_ctor.named_children
                    if c.type == "class_parameters"
                ),
                None,
            )
            if params_node:
                ctor_params: List[Dict[str, Any]] = []
                for p in params_node.named_children:
                    if p.type == "class_parameter":
                        n = next(
                            (c for c in p.named_children if c.type == "identifier"),
                            None,
                        )
                        t = next(
                            (
                                c
                                for c in p.named_children
                                if c.type in ("user_type", "nullable_type")
                            ),
                            None,
                        )
                        ctor_params.append(
                            {
                                "name": self._text_of(n) if n else "",
                                "type": self._text_of(t) if t else None,
                            }
                        )
                cls._metadata["primary_constructor_params"] = ctor_params
        return cls

    def visit_object_declaration(self, node: Any) -> IRClassDef:
        """object Singleton { val x = 1 }"""
        name_node = next(
            (c for c in node.named_children if c.type == "identifier"), None
        )
        name = self._text_of(name_node) if name_node else "object"
        body_node = next(
            (c for c in node.named_children if c.type == "class_body"), None
        )
        body = self._parse_class_body(body_node) if body_node else []
        cls = IRClassDef(
            name=name,
            bases=[],
            body=body,
            source_language=self.language,
            loc=self._get_location(node),
        )
        cls._metadata["kind"] = "object"
        return cls

    def visit_companion_object(self, node: Any) -> IRClassDef:
        """companion object { val X = 1 }"""
        name_node = next(
            (c for c in node.named_children if c.type == "identifier"), None
        )
        name = self._text_of(name_node) if name_node else "Companion"
        body_node = next(
            (c for c in node.named_children if c.type == "class_body"), None
        )
        body = self._parse_class_body(body_node) if body_node else []
        cls = IRClassDef(
            name=name,
            bases=[],
            body=body,
            source_language=self.language,
            loc=self._get_location(node),
        )
        cls._metadata["kind"] = "companion_object"
        return cls

    # ------------------------------------------------------------------
    # Properties / assignments
    # ------------------------------------------------------------------

    def visit_property_declaration(self, node: Any) -> Optional[IRAssign]:
        """val x = 5 / var name: String = "hi" """
        var_decl = next(
            (c for c in node.named_children if c.type == "variable_declaration"), None
        )
        if var_decl is None:
            return None

        name_node = next(
            (c for c in var_decl.named_children if c.type == "identifier"), None
        )
        type_node = next(
            (
                c
                for c in var_decl.named_children
                if c.type in ("user_type", "nullable_type", "function_type")
            ),
            None,
        )
        name = self._text_of(name_node) if name_node else ""

        # Find the value: named child AFTER "=" sign
        value_node: Optional[Any] = None
        after_eq = False
        for child in node.children:
            if child.type == "=" and not child.is_named:
                after_eq = True
                continue
            if after_eq and child.is_named:
                value_node = child
                break

        value_ir: IRExpr
        if value_node is not None:
            visited = self.visit(value_node)
            value_ir = (
                cast(IRExpr, visited) if visited is not None else IRConstant(value=None)
            )
        else:
            value_ir = IRConstant(value=None)

        assign = IRAssign(
            targets=[IRName(id=name, loc=self._get_location(name_node))],
            value=value_ir,
            loc=self._get_location(node),
            source_language=self.language,
        )
        if type_node:
            assign._metadata["type_annotation"] = self._text_of(type_node)
        # Record val/var mutability
        is_val = any(c.type == "val" for c in node.children)
        assign._metadata["mutable"] = not is_val
        return assign

    def visit_assignment(self, node: Any) -> Optional[IRAssign]:
        """x = newValue  /  x += 1"""
        named = node.named_children
        if len(named) < 2:
            return None
        target = named[0]
        value = named[-1]
        target_ir = self.visit(target)
        value_ir = self.visit(value)
        return IRAssign(
            targets=[
                (
                    cast(IRExpr, target_ir)
                    if target_ir
                    else IRName(id=self._text_of(target))
                )
            ],
            value=cast(IRExpr, value_ir) if value_ir else IRConstant(value=None),
            loc=self._get_location(node),
            source_language=self.language,
        )

    # ------------------------------------------------------------------
    # Control flow
    # ------------------------------------------------------------------

    def visit_return_expression(self, node: Any) -> IRReturn:
        """return expr"""
        # Named children: at most one expression
        val_node = next(
            (c for c in node.named_children if c.type not in ("@", "return")), None
        )
        value: Optional[IRExpr] = None
        if val_node is not None:
            visited = self.visit(val_node)
            if visited is not None:
                value = cast(IRExpr, visited)
        return IRReturn(
            value=value,
            loc=self._get_location(node),
            source_language=self.language,
        )

    def visit_if_expression(self, node: Any) -> IRIf:
        """if (cond) { ... } else { ... }"""
        # Find condition between ( and )
        cond_ir: Optional[IRExpr] = None
        in_paren = False
        for child in node.children:
            if child.type == "(":
                in_paren = True
                continue
            if child.type == ")":
                in_paren = False
                continue
            if in_paren and child.is_named:
                visited = self.visit(child)
                if visited is not None:
                    cond_ir = cast(IRExpr, visited)
                break

        # consequence: first block after )
        blocks = [c for c in node.named_children if c.type == "block"]
        then_body: List[IRNode] = self._visit_block(blocks[0]) if blocks else []
        else_body: List[IRNode] = (
            self._visit_block(blocks[1]) if len(blocks) > 1 else []
        )

        return IRIf(
            test=cond_ir or IRConstant(value=None),
            body=then_body,
            orelse=else_body,
            loc=self._get_location(node),
            source_language=self.language,
        )

    def visit_when_expression(self, node: Any) -> IRIf:
        """when (x) { ... } — simplified to nested if/else stub.

        [20260303_BUGFIX] Extract only the value (last named child) of each
        when_entry rather than passing the whole entry to _visit_block, which
        previously mixed conditions and bodies into all_stmts.
        """
        # Extract the when subject (condition) if present
        subject_node = next(
            (c for c in node.named_children if c.type == "when_subject"), None
        )
        test_ir: IRNode
        if subject_node is not None:
            expr = next(
                (
                    c
                    for c in subject_node.named_children
                    if c.type not in ("val", "var")
                ),
                None,
            )
            visited = self.visit(expr) if expr is not None else None
            test_ir = (
                cast(IRExpr, visited) if visited is not None else IRConstant(value=True)
            )
        else:
            test_ir = IRConstant(value=True)

        all_stmts: List[IRNode] = []
        for child in node.named_children:
            if child.type != "when_entry":
                continue
            entry_named = child.named_children
            if not entry_named:
                continue
            # The body of the entry is its last named child; any earlier named
            # children are the match conditions.  For `else ->` entries there is
            # only one named child (the body expression / block).
            body_child = entry_named[-1]
            if body_child.type == "block":
                all_stmts.extend(self._visit_block(body_child))
            else:
                res = self.visit(body_child)
                if res is None:
                    pass
                elif isinstance(res, list):
                    all_stmts.extend(r for r in res if r is not None)
                else:
                    all_stmts.append(cast(IRNode, res))

        return IRIf(
            test=cast(IRExpr, test_ir),
            body=all_stmts,
            orelse=[],
            loc=self._get_location(node),
            source_language=self.language,
        )

    def visit_for_statement(self, node: Any) -> IRFor:
        """for (item in collection) { ... }"""
        # Find loop variable (variable_declaration), iterable, and body
        var_node = next(
            (c for c in node.named_children if c.type == "variable_declaration"), None
        )
        # Iterable is the named child between "in" keyword and ")"
        iterable_ir: Optional[IRExpr] = None
        past_in = False
        for child in node.children:
            if child.type == "in":
                past_in = True
                continue
            if past_in and child.type == ")":
                break
            if past_in and child.is_named:
                visited = self.visit(child)
                if visited is not None:
                    iterable_ir = cast(IRExpr, visited)
                break

        loop_var: Optional[str] = None
        if var_node:
            n = next(
                (c for c in var_node.named_children if c.type == "identifier"), None
            )
            loop_var = self._text_of(n) if n else None

        # [20260303_BUGFIX] Support single-statement (no-brace) for bodies.
        # tree-sitter gives the body as the last non-variable_declaration named child.
        named_non_var = [
            c for c in node.named_children if c.type != "variable_declaration"
        ]
        body_node = next((c for c in named_non_var if c.type == "block"), None)
        if body_node is not None:
            body = self._visit_block(body_node)
        elif len(named_non_var) >= 2:
            # Last child is the body (second-to-last is the iterable)
            stmt_node = named_non_var[-1]
            res = self.visit(stmt_node)
            if res is None:
                body = []
            elif isinstance(res, list):
                body = [r for r in res if r is not None]
            else:
                body = [cast(IRNode, res)]
        else:
            body = []
        ir_for = IRFor(
            target=IRName(id=loop_var or "_"),
            iter=iterable_ir or IRConstant(value=None),
            body=body,
            loc=self._get_location(node),
            source_language=self.language,
        )
        return ir_for

    def visit_while_statement(self, node: Any) -> IRFor:
        """while (cond) { ... }"""
        # Condition is between ( and )
        cond_ir: Optional[IRExpr] = None
        in_paren = False
        for child in node.children:
            if child.type == "(":
                in_paren = True
                continue
            if child.type == ")":
                in_paren = False
                continue
            if in_paren and child.is_named:
                visited = self.visit(child)
                if visited is not None:
                    cond_ir = cast(IRExpr, visited)
                break

        # [20260303_BUGFIX] Support single-statement (no-brace) while bodies.
        # tree-sitter places the body as the last named child in both cases.
        body_node = next((c for c in node.named_children if c.type == "block"), None)
        if body_node is not None:
            body = self._visit_block(body_node)
        else:
            last = node.named_children[-1] if node.named_children else None
            if last is not None and last.type != "block":
                res = self.visit(last)
                if res is None:
                    body = []
                elif isinstance(res, list):
                    body = [r for r in res if r is not None]
                else:
                    body = [cast(IRNode, res)]
            else:
                body = []
        ir_for = IRFor(
            target=IRName(id="_while"),
            iter=cond_ir or IRConstant(value=True),
            body=body,
            loc=self._get_location(node),
            source_language=self.language,
        )
        ir_for._metadata["kind"] = "while"
        return ir_for

    def visit_do_while_statement(self, node: Any) -> IRFor:
        """do { ... } while (cond)"""
        body_node = next((c for c in node.named_children if c.type == "block"), None)
        body = self._visit_block(body_node)
        ir_for = IRFor(
            target=IRName(id="_do_while"),
            iter=IRConstant(value=True),
            body=body,
            loc=self._get_location(node),
            source_language=self.language,
        )
        ir_for._metadata["kind"] = "do_while"
        return ir_for

    def visit_break_expression(self, node: Any) -> IRBreak:
        return IRBreak(loc=self._get_location(node), source_language=self.language)

    def visit_continue_expression(self, node: Any) -> IRContinue:
        return IRContinue(loc=self._get_location(node), source_language=self.language)

    # ------------------------------------------------------------------
    # Expressions
    # ------------------------------------------------------------------

    def visit_call_expression(self, node: Any) -> IRCall:
        """greet("world") / obj.method() / println(x)"""
        named = node.named_children
        if not named:
            return IRCall(
                func=IRName(id="unknown"),
                args=[],
                loc=self._get_location(node),
                source_language=self.language,
            )

        func_node = named[0]
        func_ir = self.visit(func_node)
        func_name_ir: IRExpr = (
            cast(IRExpr, func_ir) if func_ir else IRName(id=self._text_of(func_node))
        )

        args_node = next((c for c in named if c.type == "value_arguments"), None)
        args: List[IRExpr] = []
        if args_node:
            for arg in args_node.named_children:
                if arg.type in ("value_argument", "annotated_expression"):
                    # value_argument: optional name "=" expression; just get expression
                    expr_children = [
                        c
                        for c in arg.named_children
                        if c.type not in ("identifier", "=")
                    ]
                    if expr_children:
                        visited = self.visit(expr_children[-1])
                        if visited is not None:
                            args.append(cast(IRExpr, visited))

        return IRCall(
            func=func_name_ir,
            args=args,
            loc=self._get_location(node),
            source_language=self.language,
        )

    def visit_binary_expression(self, node: Any) -> IRNode:
        """a + b / x == y — comparison/logical ops fall back to IRConstant."""
        children = node.children
        if len(children) < 3:
            return IRConstant(value=None, loc=self._get_location(node))
        left_node, op_node, right_node = children[0], children[1], children[2]
        op_text = self._text_of(op_node)
        op = _BINOP_MAP.get(op_text)
        if op is None:
            # Comparison / logical ops — return source text as constant
            return IRConstant(value=self._text_of(node), loc=self._get_location(node))
        left_ir = (
            self.visit(left_node) if left_node.is_named else IRConstant(value=None)
        )
        right_ir = (
            self.visit(right_node) if right_node.is_named else IRConstant(value=None)
        )
        return IRBinaryOp(
            op=op,
            left=cast(IRExpr, left_ir) if left_ir else IRConstant(value=None),
            right=cast(IRExpr, right_ir) if right_ir else IRConstant(value=None),
            loc=self._get_location(node),
            source_language=self.language,
        )

    def visit_infix_expression(self, node: Any) -> IRNode:
        """a and b / a or b / a xor b

        [20260303_BUGFIX] Return type widened to IRNode: visit_binary_expression
        can return IRConstant (for non-arithmetic operators) or IRBinaryOp.
        """
        result = self.visit_binary_expression(node)
        # Store original infix operator in metadata
        children = node.children
        if len(children) >= 2:
            result._metadata["infix_op"] = self._text_of(children[1])
        return result

    def visit_prefix_expression(self, node: Any) -> IRExpr:
        """!x / -y"""
        named = node.named_children
        if named:
            visited = self.visit(named[-1])
            if visited is not None:
                return cast(IRExpr, visited)
        return IRConstant(value=None, loc=self._get_location(node))

    def visit_postfix_expression(self, node: Any) -> IRExpr:
        """x!! / x?"""
        named = node.named_children
        if named:
            visited = self.visit(named[0])
            if visited is not None:
                return cast(IRExpr, visited)
        return IRConstant(value=None, loc=self._get_location(node))

    def visit_navigation_expression(self, node: Any) -> IRName:
        """obj.method / pkg.Class"""
        return IRName(
            id=self._text_of(node),
            loc=self._get_location(node),
        )

    def visit_identifier(self, node: Any) -> IRName:
        return IRName(id=self._text_of(node), loc=self._get_location(node))

    def visit_simple_identifier(self, node: Any) -> IRName:
        return IRName(id=self._text_of(node), loc=self._get_location(node))

    # ------------------------------------------------------------------
    # Literals
    # ------------------------------------------------------------------

    def visit_number_literal(self, node: Any) -> IRConstant:
        raw = self._text_of(node)
        try:
            val: Any = int(raw) if "." not in raw else float(raw)
        except ValueError:
            val = raw
        return IRConstant(value=val, loc=self._get_location(node))

    def visit_string_literal(self, node: Any) -> IRConstant:
        return IRConstant(
            value=self._text_of(node),
            loc=self._get_location(node),
        )

    def visit_boolean_literal(self, node: Any) -> IRConstant:
        return IRConstant(
            value=self._text_of(node) == "true",
            loc=self._get_location(node),
        )

    def visit_null(self, node: Any) -> IRConstant:
        return IRConstant(value=None, loc=self._get_location(node))

    def visit_this_expression(self, node: Any) -> IRName:
        return IRName(id="this", loc=self._get_location(node))

    def visit_super_expression(self, node: Any) -> IRName:
        return IRName(id="super", loc=self._get_location(node))

    def visit_range_expression(self, node: Any) -> IRExpr:
        """1..10"""
        return IRConstant(value=self._text_of(node), loc=self._get_location(node))

    def visit_check_expression(self, node: Any) -> IRConstant:
        """x is String / x !is Int — emit source as constant."""
        return IRConstant(value=self._text_of(node), loc=self._get_location(node))

    def visit_parenthesized_expression(self, node: Any) -> Optional[IRExpr]:
        """(expr)"""
        named = node.named_children
        if named:
            return cast(Optional[IRExpr], self.visit(named[0]))
        return None

    def visit_try_catch_expression(self, node: Any) -> Optional[IRNode]:
        """try { ... } catch (e: Exception) { ... }"""
        block = self._visit_statements(node)
        if block:
            return block[0] if len(block) == 1 else None
        return None

    def visit_anonymous_function(self, node: Any) -> IRFunctionDef:
        """fun(a: Int): Int { return a + 1 }"""
        params_node = next(
            (c for c in node.named_children if c.type == "function_value_parameters"),
            None,
        )
        params = self._parse_function_value_parameters(params_node)
        body_node = next(
            (c for c in node.named_children if c.type in ("function_body", "block")),
            None,
        )
        body = self._visit_block(body_node)
        fn = IRFunctionDef(
            name="<anonymous>",
            params=params,
            body=body,
            return_type=None,
            source_language=self.language,
            loc=self._get_location(node),
        )
        fn._metadata["kind"] = "anonymous_function"
        return fn


# ---------------------------------------------------------------------------
# Normalizer
# ---------------------------------------------------------------------------


class KotlinNormalizer(BaseNormalizer):
    """
    Normalizes Kotlin source code to Unified IR using tree-sitter-kotlin.

    [20260303_FEATURE] Kotlin language support for:
    - Function and extension function extraction (extract_code)
    - Class, data class, interface, object extraction as IRClassDef
    - Import tracking via IRImport
    - Property declarations via IRAssign
    - Control flow: if / for / while / when / do-while / break / continue
    - Expression analysis: binary ops, calls, navigation, lambdas
    - Anonymous functions and lambda literals

    Supported file extensions: .kt, .kts
    """

    @property
    def language(self) -> str:
        return "kotlin"

    _MAX_CACHE: int = 16

    def __init__(self) -> None:
        self._tree_cache: Dict[int, Any] = (
            {}
        )  # [20260303_BUGFIX] instance-level, not class-level
        self._ts_language = Language(tree_sitter_kotlin.language())  # type: ignore[call-arg]
        self._parser = Parser()
        self._parser.language = self._ts_language
        self._visitor: Optional[KotlinVisitor] = None

    def normalize(self, source: str, filename: str = "<string>") -> IRModule:
        """Parse Kotlin source and return a Unified IRModule."""
        tree = self._parse_cached(source)
        self._visitor = KotlinVisitor(source)
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
