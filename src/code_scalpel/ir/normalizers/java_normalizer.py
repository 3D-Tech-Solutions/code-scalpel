"""
Java Normalizer - Converts Java CST (tree-sitter) to Unified IR.

This module implements the normalization logic for Java, mapping verbose
Java constructs to the simplified Unified IR.

Key Mappings:
- method_declaration -> IRFunction
- class_declaration -> IRClass
- variable_declarator -> IRAssignment
- if_statement -> IRIf
- while_statement -> IRWhile
- for_statement -> IRFor
"""

from typing import Any, cast

import tree_sitter_java
from tree_sitter import Language, Parser

from ..nodes import (  # [20251214_FEATURE] Add location tracking for polyglot extraction; [20251215_FEATURE] v2.0.0 - Additional nodes for complete Java support
    IRAssign,
    IRBinaryOp,
    IRCall,
    IRClassDef,
    IRConstant,
    IRFor,
    IRFunctionDef,
    IRIf,
    IRImport,
    IRModule,
    IRName,
    IRNode,
    IRParameter,
    IRRaise,
    IRReturn,
    IRSwitch,
    IRTry,
    IRWhile,
    SourceLocation,
)
from ..operators import BinaryOperator
from .base import BaseNormalizer
from .tree_sitter_visitor import TreeSitterVisitor


class JavaVisitor(TreeSitterVisitor):
    """Visitor that converts Java CST nodes to IR nodes."""

    @property
    def language(self) -> str:  # [20251220_BUGFIX] language should be a property
        return "java"

    def __init__(self, source: str = ""):
        super().__init__()
        self.ctx.source = source

    def _get_node_type(self, node: Any) -> str:
        return node.type

    def _get_text(self, node: Any) -> str:
        return self.ctx.source[node.start_byte : node.end_byte]

    def _get_location(self, node: Any) -> Any:
        # [20251214_FEATURE] Proper location tracking for polyglot extraction
        if node is None:
            return None
        return SourceLocation(
            line=node.start_point[0] + 1,  # tree-sitter is 0-indexed
            column=node.start_point[1],
            end_line=node.end_point[0] + 1,
            end_column=node.end_point[1],
        )

    def _get_children(self, node: Any) -> list[Any]:
        return node.children

    def _get_named_children(self, node: Any) -> list[Any]:
        return [c for c in node.children if c.is_named]

    def _get_child_by_field(self, node: Any, field_name: str) -> Any | None:
        return node.child_by_field_name(field_name)

    def _get_children_by_field(self, node: Any, field_name: str) -> list[Any]:
        return node.children_by_field_name(field_name)

    # [20251220_BUGFIX] Helper methods for proper type casting and normalization
    def _norm_expr(self, node: Any | None) -> Any | None:
        """Normalize node to expression with type casting."""
        if node is None:
            return None
        result = self.visit(node)
        return cast(Any, result) if not isinstance(result, list) else None

    def _norm_expr_list(self, nodes: list[Any] | None) -> list[Any]:
        """Normalize list of nodes to flat list of expressions."""
        if nodes is None:
            return []
        results = []
        for node in nodes:
            result = self.visit(node)
            if not isinstance(result, list) and result is not None:
                results.append(result)
        return results

    def visit_program(self, node: Any) -> IRModule:
        """Root node of a Java file."""
        body = []
        for child in node.children:
            # Skip comments and whitespace
            if not child.is_named:
                continue

            res = self.visit(child)
            if res:
                if isinstance(res, list):
                    body.extend(res)
                else:
                    body.append(res)

        return IRModule(body=body, source_language=self.language)

    # =========================================================================
    # Package and Import Handlers - [20251215_FEATURE] v2.0.0 Java imports
    # =========================================================================

    def visit_package_declaration(self, node: Any) -> IRImport:
        """
        package com.example.app;

        [20251215_FEATURE] Package declarations become IRImport with is_package=True.
        """
        # package_declaration has identifier children for the package path
        name_parts = []
        for child in node.children:
            if child.type == "scoped_identifier":
                name_parts.append(self.get_text(child))
            elif child.type == "identifier":
                name_parts.append(self.get_text(child))

        package_name = ".".join(name_parts) if name_parts else self.get_text(node)

        return IRImport(
            module=package_name,
            names=[],
            is_star=False,
            loc=self._get_location(node),
        )

    def visit_import_declaration(self, node: Any) -> IRImport:
        """
        import java.util.List;
        import java.util.*;
        import static java.lang.Math.PI;

        [20251215_FEATURE] Java imports mapped to IRImport.
        """
        # [20251215_REFACTOR] Remove unused locals while preserving import handling semantics.
        # Check for wildcard import (import x.*)
        is_star = any(c.type == "asterisk" for c in node.children)

        # Get the import path
        module_path = ""
        for child in node.children:
            if child.type == "scoped_identifier":
                module_path = self.get_text(child)
            elif child.type == "identifier":
                module_path = self.get_text(child)

        # For "import java.util.List", module is "java.util", name is "List"
        # For "import java.util.*", module is "java.util", is_star=True
        parts = module_path.rsplit(".", 1)
        if len(parts) == 2 and not is_star:
            module = parts[0]
            names = [parts[1]]
        else:
            module = module_path
            names = []

        return IRImport(
            module=module,
            names=names,
            is_star=is_star,
            loc=self._get_location(node),
        )

    def visit_class_declaration(self, node: Any) -> IRClassDef:
        """
        class MyClass { ... }
        """
        name_node = node.child_by_field_name("name")
        name = self.get_text(name_node) if name_node else "Anonymous"

        body_node = node.child_by_field_name("body")
        body = []

        # [20251215_FEATURE] Capture inheritance, interfaces, annotations, and type params
        bases: list[Any] = []
        superclass_node = node.child_by_field_name("superclass")
        if superclass_node:
            bases.extend(IRName(id=b) for b in self._extract_type_names(superclass_node))

        interfaces_node = node.child_by_field_name("interfaces")
        if interfaces_node:
            bases.extend(IRName(id=b) for b in self._extract_type_names(interfaces_node))

        decorators = self._collect_annotations(node)
        type_params = self._extract_type_params(node.child_by_field_name("type_parameters"))

        if body_node:
            for child in body_node.children:
                if child.type == "method_declaration":
                    method = self.visit(child)
                    if method:
                        body.append(method)
                elif child.type == "constructor_declaration":
                    # [20251215_FEATURE] v2.0.0 - Constructor support
                    constructor = self.visit(child)
                    if constructor:
                        body.append(constructor)
                elif child.type == "field_declaration":
                    # [20251215_FEATURE] v2.0.0 - Field declaration support
                    fields = self.visit(child)
                    if fields:
                        if isinstance(fields, list):
                            body.extend(fields)
                        else:
                            body.append(fields)
                elif child.type in ("class_declaration", "record_declaration"):
                    nested = self.visit(child)
                    if nested:
                        body.append(nested)

        class_ir = IRClassDef(
            name=name,
            bases=bases,
            body=body,
            decorators=cast(list[Any], decorators),  # [20251220_BUGFIX] Cast decorators
            source_language=self.language,
            loc=self._get_location(node),
        )

        if type_params:
            class_ir._metadata["type_params"] = type_params

        return class_ir

    # =========================================================================
    # Record Declaration Handler - [20251215_FEATURE] v2.0.1 Java 16+ records
    # =========================================================================

    def visit_record_declaration(self, node: Any) -> IRClassDef:
        """
        public record Point(int x, int y) { ... }

        [20251215_FEATURE] Java 16+ record declarations become IRClassDef.
        Records are immutable data classes with auto-generated methods.
        """
        name_node = node.child_by_field_name("name")
        name = self.get_text(name_node) if name_node else "Anonymous"

        body = []

        # Record parameters become fields (in the formal_parameters node)
        params_node = node.child_by_field_name("parameters")
        if params_node:
            for child in params_node.children:
                if child.type == "formal_parameter":
                    p_name = child.child_by_field_name("name")
                    if p_name:
                        # Create a field assignment for each record component
                        body.append(
                            IRAssign(
                                targets=[IRName(id=self.get_text(p_name))],
                                value=IRConstant(value=None),
                                loc=self._get_location(child),
                            )
                        )

        # Process body if it exists (compact constructor, methods)
        body_node = node.child_by_field_name("body")
        if body_node:
            for child in body_node.children:
                if child.type == "method_declaration":
                    method = self.visit(child)
                    if method:
                        body.append(method)
                elif child.type == "compact_constructor_declaration":
                    # Compact constructor for records
                    constructor = self.visit(child)
                    if constructor:
                        body.append(constructor)

        return IRClassDef(
            name=name,
            bases=[IRName(id="Record")],  # [20251220_BUGFIX] Use IRName instead of string
            body=body,
            source_language=self.language,
            loc=self._get_location(node),
        )

    def visit_compact_constructor_declaration(self, node: Any) -> IRFunctionDef:
        """
        public Point { ... }  // Compact constructor for records

        [20251215_FEATURE] Compact constructors in Java 16+ records.
        """
        name_node = node.child_by_field_name("name")
        name = self.get_text(name_node) if name_node else "Unknown"

        body_node = node.child_by_field_name("body")
        body_stmts = []
        if body_node:
            body_stmts = self.visit(body_node)

        return IRFunctionDef(
            name="__init__",
            params=[],  # Compact constructors have implicit params
            body=(body_stmts if isinstance(body_stmts, list) else [body_stmts] if body_stmts else []),
            return_type=name,
            source_language=self.language,
            loc=self._get_location(node),
        )

    # =========================================================================
    # Constructor Handler - [20251215_FEATURE] v2.0.0 Java constructors
    # =========================================================================

    def visit_constructor_declaration(self, node: Any) -> IRFunctionDef:
        """
        public MyClass(int x, String y) { ... }

        [20251215_FEATURE] Constructors become IRFunctionDef with name "__init__".
        """
        name_node = node.child_by_field_name("name")
        class_name = self.get_text(name_node) if name_node else "Unknown"

        decorators = self._collect_annotations(node)
        type_params = self._extract_type_params(node.child_by_field_name("type_parameters"))

        # Parameters
        params = []
        params_node = node.child_by_field_name("parameters")
        if params_node:
            for child in params_node.children:
                if child.type == "formal_parameter":
                    p_name = child.child_by_field_name("name")
                    p_type = child.child_by_field_name("type")
                    annotations = self._collect_annotations(child)
                    if p_name:
                        # [20251215_BUGFIX] v2.0.0 - Use type_annotation not annotation
                        param = IRParameter(
                            name=self.get_text(p_name),
                            type_annotation=(self.get_text(p_type) if p_type else None),
                        )
                        if annotations:
                            param._metadata["annotations"] = [a.id if isinstance(a, IRName) else a for a in annotations]
                        params.append(param)

        # Body
        body_node = node.child_by_field_name("body")
        body_stmts = []
        if body_node:
            body_stmts = self.visit(body_node)

        constructor = IRFunctionDef(
            name="__init__",  # Use Python convention for constructors
            params=params,
            body=(body_stmts if isinstance(body_stmts, list) else [body_stmts] if body_stmts else []),
            return_type=class_name,  # Constructor "returns" instance of class
            source_language=self.language,
            loc=self._get_location(node),
            decorators=cast(list[Any], decorators),  # [20251220_BUGFIX] Cast decorators
        )

        if type_params:
            constructor._metadata["type_params"] = type_params

        return constructor

    def visit_field_declaration(self, node: Any) -> list[IRAssign]:
        """
        private int x = 5;
        public String name, value;

        [20251215_FEATURE] Field declarations become IRAssign statements.
        """
        assignments = []

        for child in node.children:
            if child.type == "variable_declarator":
                assign = self._norm_expr(child)
                if isinstance(assign, IRAssign):  # [20251220_BUGFIX] Type check
                    assignments.append(assign)

        return assignments  # [20251220_BUGFIX] Always return list, never None

    def visit_method_declaration(self, node: Any) -> IRFunctionDef:
        """
        public void myMethod(int x) { ... }
        """
        name_node = node.child_by_field_name("name")
        name = self.get_text(name_node)

        decorators = self._collect_annotations(node)
        type_params = self._extract_type_params(node.child_by_field_name("type_parameters"))
        return_type_node = node.child_by_field_name("type")
        return_type = self.get_text(return_type_node) if return_type_node else None

        # Parameters
        params = []
        params_node = node.child_by_field_name("parameters")
        if params_node:
            for child in params_node.children:
                if child.type == "formal_parameter":
                    p_name = child.child_by_field_name("name")
                    p_type = child.child_by_field_name("type")
                    annotations = self._collect_annotations(child)
                    if p_name:
                        param = IRParameter(
                            name=self.get_text(p_name),
                            type_annotation=(self.get_text(p_type) if p_type else None),
                        )
                        if annotations:
                            param._metadata["annotations"] = [a.id if isinstance(a, IRName) else a for a in annotations]
                        params.append(param)

        # Body
        body_node = node.child_by_field_name("body")
        body_stmts = []
        if body_node:
            # visit_block returns List[IRNode]
            result = self.visit(body_node)
            body_stmts = result if isinstance(result, list) else []  # [20251220_BUGFIX] Handle list

        func = IRFunctionDef(
            name=name,
            params=params,
            body=body_stmts,
            return_type=return_type,
            source_language=self.language,
            loc=self._get_location(node),  # [20251214_FEATURE] Add location for extraction
            decorators=cast(list[Any], decorators),  # [20251220_BUGFIX] Cast decorators
        )

        if type_params:
            func._metadata["type_params"] = type_params

        return func

    def visit_block(self, node: Any) -> list[IRNode]:
        """{ stmt1; stmt2; }"""
        statements = []
        for child in node.children:
            if not child.is_named:
                continue
            stmt = self.visit(child)
            if stmt:
                statements.append(stmt)
        return statements

    def visit_local_variable_declaration(self, node: Any) -> Any:
        """
        int x = 5;
        int x, y = 10;
        """
        # This node contains type and declarators
        # We want to return a list of assignments/declarations
        declarators = []

        for child in node.children:
            if child.type == "variable_declarator":
                declarators.append(self.visit(child))

        # If single declarator, return it. If multiple, return list?
        # IRBlock expects statements.
        # For simplicity, let's return the first one or a list if multiple
        if len(declarators) == 1:
            return declarators[0]
        return declarators

    def visit_variable_declarator(self, node: Any) -> IRAssign:
        """x = 5"""
        name_node = node.child_by_field_name("name")
        value_node = node.child_by_field_name("value")

        target = IRName(id=self.get_text(name_node))
        value = (
            self._norm_expr(value_node) if value_node else IRConstant(value=None)
        )  # [20251220_BUGFIX] Normalize value

        return IRAssign(targets=[target], value=cast(Any, value))

    def visit_expression_statement(self, node: Any) -> Any:
        """x = 5; or func();"""
        # Usually wraps an assignment or method invocation
        for child in node.children:
            if child.type != ";":
                return self.visit(child)
        return None

    def visit_assignment_expression(self, node: Any) -> IRAssign:
        """x = y"""
        left = node.child_by_field_name("left")
        right = node.child_by_field_name("right")

        return IRAssign(
            targets=[cast(Any, self._norm_expr(left))],
            value=cast(Any, self._norm_expr(right)),
        )  # [20251220_BUGFIX] Normalize expressions

    def visit_method_invocation(self, node: Any) -> IRCall:
        """obj.method(arg)"""
        name_node = node.child_by_field_name("name")
        object_node = node.child_by_field_name("object")
        args_node = node.child_by_field_name("arguments")

        func_name = self.get_text(name_node)
        if object_node:
            # method call on object
            obj_text = self.get_text(object_node)
            # We might represent this as a specialized IR node or just a name "obj.method"
            # For now, let's use IRName with the full dotted path if simple
            func_name = f"{obj_text}.{func_name}"

        args = []
        if args_node:
            for child in args_node.children:
                if child.is_named:
                    args.append(self.visit(child))

        return IRCall(func=IRName(id=func_name), args=args, kwargs={})

    def visit_if_statement(self, node: Any) -> IRIf:
        """if (cond) { ... } else { ... }"""
        condition_node = node.child_by_field_name("condition")
        consequence_node = node.child_by_field_name("consequence")
        alternative_node = node.child_by_field_name("alternative")

        condition = self._norm_expr(condition_node) if condition_node else None  # [20251220_BUGFIX] Normalize condition
        consequence = self.visit(consequence_node) if consequence_node else []
        alternative = self.visit(alternative_node) if alternative_node else []

        # Helper to ensure list of nodes
        def to_list(n):
            if isinstance(n, list):
                return n
            return [n] if n else []

        return IRIf(
            test=cast(Any, condition),
            body=to_list(consequence),
            orelse=to_list(alternative),  # [20251220_BUGFIX] Cast condition
        )

    def visit_while_statement(self, node: Any) -> IRWhile:
        """while (cond) { ... }"""
        condition = self._norm_expr(node.child_by_field_name("condition"))  # [20251220_BUGFIX] Normalize condition
        body = self.visit(node.child_by_field_name("body"))

        def to_list(n):
            if isinstance(n, list):
                return n
            return [n] if n else []

        return IRWhile(test=cast(Any, condition), body=to_list(body))  # [20251220_BUGFIX] Cast condition

    def visit_return_statement(self, node: Any) -> IRReturn:
        """return x;"""
        # return statement has children, usually 'return' keyword and expression and ';'
        expr = None
        for child in node.children:
            if child.is_named:
                expr = self._norm_expr(child)  # [20251220_BUGFIX] Normalize expression
                break

        return IRReturn(value=cast(Any, expr))  # [20251220_BUGFIX] Cast expression

    def visit_binary_expression(self, node: Any) -> IRBinaryOp:
        """a + b"""
        left = self._norm_expr(node.child_by_field_name("left"))  # [20251220_BUGFIX] Normalize left
        right = self._norm_expr(node.child_by_field_name("right"))  # [20251220_BUGFIX] Normalize right
        operator_text = self.get_text(node.child_by_field_name("operator"))

        # Map operator text to BinaryOperator enum if possible, or just use text for now if allowed
        # The IRBinaryOp expects a BinaryOperator enum usually, but let's check definition.
        # It says op: BinaryOperator = None.
        # For now, we might need a mapping.
        # Simplified mapping:
        op_map = {
            "+": BinaryOperator.ADD,
            "-": BinaryOperator.SUB,
            "*": BinaryOperator.MUL,
            "/": BinaryOperator.DIV,
            "%": BinaryOperator.MOD,
        }
        op = op_map.get(operator_text, BinaryOperator.ADD)  # Default to ADD if unknown for now

        return IRBinaryOp(left=cast(Any, left), op=op, right=cast(Any, right))  # [20251220_BUGFIX] Cast operands

    def visit_identifier(self, node: Any) -> IRName:
        return IRName(id=self.get_text(node))

    def visit_decimal_integer_literal(self, node: Any) -> IRConstant:
        return IRConstant(value=int(self.get_text(node)))

    def visit_string_literal(self, node: Any) -> IRConstant:
        # Strip quotes
        text = self.get_text(node)
        return IRConstant(value=text[1:-1])

    def visit_true(self, node: Any) -> IRConstant:
        return IRConstant(value=True)

    def visit_false(self, node: Any) -> IRConstant:
        return IRConstant(value=False)

    # =========================================================================
    # Try/Catch Handler - [20251215_FEATURE] v2.0.0 Java exception handling
    # =========================================================================

    def visit_try_statement(self, node: Any) -> IRTry:
        """
        try { ... } catch (Exception e) { ... } finally { ... }

        [20251215_FEATURE] Java try/catch/finally mapped to IRTry.
        """
        body = []
        handlers = []
        finalbody = []

        for child in node.children:
            if child.type == "block" and not handlers and not finalbody:
                # This is the try block (first block before any catch/finally)
                body = self.visit(child)
            elif child.type == "catch_clause":
                # catch (ExceptionType e) { ... }
                catch_body = []
                exc_type = None
                exc_name = None

                for cc in child.children:
                    if cc.type == "catch_formal_parameter":
                        for param in cc.children:
                            if param.type in (
                                "type_identifier",
                                "scoped_type_identifier",
                            ):
                                exc_type = self.get_text(param)
                            elif param.type == "identifier":
                                exc_name = self.get_text(param)
                    elif cc.type == "block":
                        catch_body = self.visit(cc)

                handlers.append(
                    {
                        "type": exc_type,
                        "name": exc_name,
                        "body": (catch_body if isinstance(catch_body, list) else [catch_body] if catch_body else []),
                    }
                )
            elif child.type == "finally_clause":
                for fc in child.children:
                    if fc.type == "block":
                        finalbody = self.visit(fc)

        return IRTry(
            body=body if isinstance(body, list) else [body] if body else [],
            handlers=handlers,
            orelse=[],  # Java doesn't have try/else
            finalbody=(finalbody if isinstance(finalbody, list) else [finalbody] if finalbody else []),
            loc=self._get_location(node),
        )

    def visit_throw_statement(self, node: Any) -> IRRaise:
        """
        throw new Exception("error");

        [20251215_FEATURE] Java throw mapped to IRRaise.
        """
        exc = None
        for child in node.children:
            if child.is_named and child.type != ";":
                exc = self._norm_expr(child)  # [20251220_BUGFIX] Normalize exception
                break

        return IRRaise(
            exc=cast(Any, exc),  # [20251220_BUGFIX] Cast exception
            cause=None,
            loc=self._get_location(node),
        )

    # =========================================================================
    # Switch Handler - [20251215_FEATURE] v2.0.0 Java switch statements
    # =========================================================================

    def visit_switch_expression(self, node: Any) -> IRSwitch:
        """
        switch (x) { case 1: ...; default: ...; }

        [20251215_FEATURE] Java switch mapped to IRSwitch.
        """
        return self._normalize_switch(node)

    def visit_switch_statement(self, node: Any) -> IRSwitch:
        """Alternative name for switch in some tree-sitter versions."""
        return self._normalize_switch(node)

    def _normalize_switch(self, node: Any) -> IRSwitch:
        """Internal switch normalization."""
        discriminant = None
        cases = []

        for child in node.children:
            if child.type == "parenthesized_expression":
                # The switch subject: switch (x)
                for inner in child.children:
                    if inner.is_named:
                        discriminant = self._norm_expr(inner)  # [20251220_BUGFIX] Normalize discriminant
                        break
            elif child.type == "switch_block":
                # Process cases
                for block_child in child.children:
                    if block_child.type in (
                        "switch_block_statement_group",
                        "switch_rule",
                    ):
                        case_values = []
                        case_body = []
                        is_default = False

                        for item in block_child.children:
                            if item.type == "switch_label":
                                label_text = self.get_text(item)
                                if "default" in label_text.lower():
                                    is_default = True
                                else:
                                    # Extract case value
                                    for lc in item.children:
                                        if lc.is_named and lc.type != "case":
                                            case_values.append(self.visit(lc))
                            elif item.is_named and item.type not in ("switch_label",):
                                stmt = self.visit(item)
                                if stmt:
                                    if isinstance(stmt, list):
                                        case_body.extend(stmt)
                                    else:
                                        case_body.append(stmt)

                        if is_default:
                            # Default case has test=None
                            cases.append((None, case_body))
                        else:
                            for cv in case_values:
                                cases.append((cv, case_body))

        return IRSwitch(
            discriminant=cast(Any, discriminant),  # [20251220_BUGFIX] Cast discriminant
            cases=cases,
            loc=self._get_location(node),
        )

    # =========================================================================
    # For Loop Handler - [20251215_FEATURE] v2.0.0 Java for loops
    # =========================================================================

    def visit_for_statement(self, node: Any) -> IRFor:
        """
        for (int i = 0; i < n; i++) { ... }

        [20251215_FEATURE] Java for loops mapped to IRFor.
        """
        init = None
        condition = None
        body = []

        for child in node.children:
            if child.type == "local_variable_declaration":
                init = self.visit(child)
            elif child.type == "assignment_expression" and init is None:
                init = self.visit(child)
            elif child.type == "binary_expression" and condition is None:
                condition = self._norm_expr(child)  # [20251220_BUGFIX] Normalize condition
            elif child.type == "update_expression":
                self.visit(child)
            elif child.type in ("block", "expression_statement"):
                body = self.visit(child)

        return IRFor(
            target=init.targets[0] if isinstance(init, IRAssign) else IRName(id="_"),
            iter=cast(Any, condition),  # [20251220_BUGFIX] Cast condition
            body=body if isinstance(body, list) else [body] if body else [],
            orelse=[],
            loc=self._get_location(node),
        )

    def visit_enhanced_for_statement(self, node: Any) -> IRFor:
        """
        for (String item : items) { ... }

        [20251215_FEATURE] Java enhanced for (foreach) loops.
        """
        target = None
        iterable = None
        body = []

        for child in node.children:
            if child.type == "identifier" and target is None:
                target = IRName(id=self.get_text(child))
            elif child.is_named and child.type not in (
                "type_identifier",
                "block",
                "identifier",
            ):
                if iterable is None:
                    iterable = self._norm_expr(child)  # [20251220_BUGFIX] Normalize iterable
            elif child.type == "block":
                body = self.visit(child)

        return IRFor(
            target=target or IRName(id="_"),
            iter=cast(Any, iterable),  # [20251220_BUGFIX] Cast iterable
            body=body if isinstance(body, list) else [body] if body else [],
            orelse=[],
            loc=self._get_location(node),
        )

    def visit_update_expression(self, node: Any) -> IRAssign | None:  # [20251220_BUGFIX] Allow None return
        """
        i++ or ++i

        [20251215_FEATURE] Update expressions become augmented assignments.

            - Lambda expressions: (x, y) -> x + y
            - Method references: String::valueOf, System.out::println
            - Constructor references: ArrayList::new
            - Stream API patterns: stream().map().filter().collect()

            - public/private/protected markers
            - static, final, abstract flags
            - Package-private default visibility
        """
        operand = None
        operator = None

        for child in node.children:
            if child.type == "identifier":
                operand = IRName(id=self.get_text(child))
            elif child.type in ("++", "--"):
                operator = self.get_text(child)

        if operand:
            # i++ becomes i = i + 1
            op = BinaryOperator.ADD if operator == "++" else BinaryOperator.SUB
            return IRAssign(
                targets=[operand],
                value=IRBinaryOp(left=operand, op=op, right=IRConstant(value=1)),
            )
        return None

    def visit_object_creation_expression(self, node: Any) -> IRCall:
        """
        new ArrayList<>()
        new Exception("error")

        [20251215_FEATURE] Object creation becomes IRCall.
        """
        type_node = node.child_by_field_name("type")
        args_node = node.child_by_field_name("arguments")

        type_name = self.get_text(type_node) if type_node else "Object"

        args = []
        if args_node:
            for child in args_node.children:
                if child.is_named:
                    args.append(self.visit(child))

        return IRCall(
            func=IRName(id=type_name),
            args=args,
            kwargs={},
        )

    # [20251215_FEATURE] Helpers for annotations, types, and generics
    def _collect_annotations(self, node: Any) -> list[IRName]:
        annotations: list[IRName] = []
        for child in node.children:
            if child.type in ("annotation", "marker_annotation"):
                name_node = child.child_by_field_name("name")
                name_text = self.get_text(name_node) if name_node else self.get_text(child)
                annotations.append(IRName(id=name_text.lstrip("@")))
            elif child.type == "modifiers":
                annotations.extend(self._collect_annotations(child))
        return annotations

    def _extract_type_params(self, node: Any | None) -> list[str]:
        if node is None:
            return []
        text = self.get_text(node).strip()
        if text.startswith("<") and text.endswith(">"):
            text = text[1:-1]
        return [part.strip() for part in text.split(",") if part.strip()]

    def _extract_type_names(self, node: Any | None) -> list[str]:
        if node is None:
            return []
        text = self.get_text(node).replace("implements", " ").replace("extends", " ").replace(",", " ")
        names = []
        for part in text.split():
            cleaned = part.strip()
            if cleaned:
                names.append(cleaned)
        return names


class JavaNormalizer(BaseNormalizer):
    """[20251224_FEATURE] Java CST normalization with comprehensive features.


    COMMUNITY TIER (Core Java AST Normalization):

    PRO TIER (Advanced Java Features):

    ENTERPRISE TIER (Advanced Analysis & Optimization):
    """

    """Normalizes Java source code to Unified IR."""

    @property
    def language(self) -> str:  # [20251220_BUGFIX] language should be a property
        return "java"

    _MAX_CACHE = 16  # [20251215_PERF] Bound cached parse trees for Java throughput
    _tree_cache: dict[int, Any] = {}

    def __init__(self):
        self.JAVA_LANGUAGE = Language(tree_sitter_java.language())
        self.parser = Parser()
        self.parser.language = self.JAVA_LANGUAGE
        self._visitor: JavaVisitor | None = None

    def normalize(self, source: str, filename: str = "<string>") -> IRModule:
        tree = self._parse_cached(source)
        self._visitor = JavaVisitor(source)
        result = self._visitor.visit(tree.root_node)
        return cast(IRModule, result)  # [20251220_BUGFIX] Cast result to IRModule

    def _parse_cached(self, source: str):
        """Parse with a small eviction cache to improve repeated Java runs."""
        key = hash(source)
        cached = self._tree_cache.get(key)
        if cached is not None:
            return cached

        tree = self.parser.parse(bytes(source, "utf8"))
        if len(self._tree_cache) >= self._MAX_CACHE:
            self._tree_cache.pop(next(iter(self._tree_cache)))
        self._tree_cache[key] = tree
        return tree

    def normalize_node(self, node: Any) -> Any:
        """Normalize a single tree-sitter node to IR."""
        if self._visitor is None:
            raise RuntimeError("normalize() must be called before normalize_node()")
        return self._visitor.visit(node)
