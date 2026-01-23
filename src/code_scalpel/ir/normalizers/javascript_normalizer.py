"""
JavaScript Normalizer - Convert tree-sitter-javascript CST to Unified IR.

This normalizer handles the NOISE of tree-sitter's Concrete Syntax Tree.
Unlike Python's ast which is already abstract, tree-sitter gives us:

    binary_expression:
        left: number_literal "5"
        "+"  <- Anonymous node (operator)
        right: number_literal "3"

We must extract semantic meaning and discard syntactic tokens.

Supported Constructs:
    - Functions: function declarations, arrow functions, methods
    - Classes: class declarations, methods, constructors
    - Control flow: if/else, for, while, switch
    - Expressions: binary ops, unary ops, calls, member access
    - Modules: import/export (ES6)

CST Node Reference (tree-sitter-javascript):
    https://github.com/tree-sitter/tree-sitter-javascript/blob/master/src/grammar.json
"""

from __future__ import annotations

import warnings
from typing import Any, cast

from ..nodes import (  # [20251215_FEATURE] v2.0.0 - New IR nodes for polyglot support
    IRAssign,
    IRAttribute,
    IRAugAssign,
    IRBinaryOp,
    IRBoolOp,
    IRBreak,
    IRCall,
    IRClassDef,
    IRCompare,
    IRConstant,
    IRContinue,
    IRDict,
    IRExport,
    IRExpr,
    IRExprStmt,
    IRFor,
    IRFunctionDef,
    IRIf,
    IRImport,
    IRList,
    IRModule,
    IRName,
    IRNode,
    IRParameter,
    IRRaise,
    IRReturn,
    IRSubscript,
    IRSwitch,
    IRTernary,
    IRTry,
    IRUnaryOp,
    IRWhile,
    SourceLocation,
)
from ..operators import (
    AugAssignOperator,
    BinaryOperator,
    BoolOperator,
    CompareOperator,
    UnaryOperator,
)
from .base import BaseNormalizer

# =============================================================================
# Operator Mappings
# =============================================================================

BINARY_OP_MAP = {
    "+": BinaryOperator.ADD,
    "-": BinaryOperator.SUB,
    "*": BinaryOperator.MUL,
    "/": BinaryOperator.DIV,
    "%": BinaryOperator.MOD,
    "**": BinaryOperator.POW,
    "<<": BinaryOperator.LSHIFT,
    ">>": BinaryOperator.RSHIFT,
    ">>>": BinaryOperator.RSHIFT,  # Unsigned right shift -> regular (best effort)
    "&": BinaryOperator.BIT_AND,
    "|": BinaryOperator.BIT_OR,
    "^": BinaryOperator.BIT_XOR,
    # [20251215_BUGFIX] Map uncommon TS operator to ADD to match legacy fallback expectations.
    "@@": BinaryOperator.ADD,
}

COMPARE_OP_MAP = {
    "==": CompareOperator.EQ,
    "===": CompareOperator.EQ,  # Strict equality -> regular (semantic diff in IR)
    "!=": CompareOperator.NE,
    "!==": CompareOperator.NE,  # Strict inequality
    "<": CompareOperator.LT,
    "<=": CompareOperator.LE,
    ">": CompareOperator.GT,
    ">=": CompareOperator.GE,
    "in": CompareOperator.IN,
    "instanceof": CompareOperator.IN,  # instanceof -> in (best effort)
}

BOOL_OP_MAP = {
    "&&": BoolOperator.AND,
    "||": BoolOperator.OR,
    "??": BoolOperator.OR,  # Nullish coalescing -> OR (best effort)
}

UNARY_OP_MAP = {
    "-": UnaryOperator.NEG,
    "+": UnaryOperator.POS,
    "!": UnaryOperator.NOT,
    "~": UnaryOperator.INVERT,
    "typeof": UnaryOperator.NOT,  # typeof -> NOT (placeholder, needs IR extension)
    "void": UnaryOperator.NOT,  # void -> NOT (placeholder)
}

AUG_ASSIGN_OP_MAP = {
    "+=": AugAssignOperator.ADD,
    "-=": AugAssignOperator.SUB,
    "*=": AugAssignOperator.MUL,
    "/=": AugAssignOperator.DIV,
    "%=": AugAssignOperator.MOD,
    "**=": AugAssignOperator.POW,
    "<<=": AugAssignOperator.LSHIFT,
    ">>=": AugAssignOperator.RSHIFT,
    "&=": AugAssignOperator.BIT_AND,
    "|=": AugAssignOperator.BIT_OR,
    "^=": AugAssignOperator.BIT_XOR,
}


class JavaScriptNormalizer(BaseNormalizer):
    """
    Normalizes JavaScript CST (from tree-sitter) to Unified IR.

    This normalizer handles the complexity of tree-sitter's concrete output,
    filtering noise tokens and mapping JavaScript-specific constructs to IR.

    Example:
        >>> normalizer = JavaScriptNormalizer()
        >>> ir = normalizer.normalize('''
        ... function add(a, b) {
        ...     return a + b;
        ... }
        ... ''')
        >>> ir.body[0].name
        'add'

    Tree-sitter dependency:
        Requires tree_sitter and tree_sitter_javascript packages:
        pip install tree-sitter tree-sitter-javascript


    COMMUNITY TIER (Core JavaScript CST Normalization):

    PRO TIER (Advanced JavaScript Features):

    ENTERPRISE TIER (Advanced Analysis & Optimization):
    """

    def __init__(self):
        self._filename: str = "<string>"
        self._source: str = ""
        self._parser: Any | None = None
        self._language: Any | None = None
        self._ensure_parser()

    # [20251220_BUGFIX] Helper methods for proper type casting
    def _norm_expr(self, node: Any) -> IRExpr | None:
        """Normalize node to IRExpr with type casting."""
        if node is None:
            return None
        result = self.normalize_node(node)
        return cast(IRExpr, result) if not isinstance(result, list) else None

    def _norm_expr_list(self, nodes: list[Any]) -> list[IRExpr]:
        """Normalize list of expression nodes to List[IRExpr]."""
        results = []
        for node in nodes:
            result = self.normalize_node(node)
            if not isinstance(result, list) and result is not None:
                results.append(cast(IRExpr, result))
        return results

    def _norm_body(self, nodes: list[Any]) -> list[IRNode]:
        """Normalize list of statement nodes."""
        results = []
        for node in nodes:
            result = self.normalize_node(node)
            if result is not None:
                if isinstance(result, list):
                    results.extend(result)
                else:
                    results.append(result)
        return results

    def _ensure_parser(self) -> None:
        """Lazily initialize tree-sitter parser."""
        if self._parser is not None:
            return

        try:
            import tree_sitter_javascript as ts_js
            from tree_sitter import Language, Parser

            self._language = Language(ts_js.language())
            self._parser = Parser(self._language)
        except ImportError as e:
            raise ImportError(
                "JavaScriptNormalizer requires tree-sitter packages. "
                "Install with: pip install tree-sitter tree-sitter-javascript"
            ) from e

    @property
    def language(self) -> str:
        return "javascript"

    def normalize(self, source: str, filename: str = "<string>") -> IRModule:
        """Parse JavaScript source and normalize to IR."""
        self._ensure_parser()
        assert self._parser is not None  # [20251220_BUGFIX] Guard parser None access
        self._filename = filename
        self._source = source

        # Parse with tree-sitter
        tree = self._parser.parse(source.encode("utf-8"))
        root = tree.root_node

        # Check for parse errors
        if root.has_error:
            # Find first error node
            error_node = self._find_error_node(root)
            if error_node:
                loc = self._make_loc(error_node)
                raise SyntaxError(f"Parse error at {loc}")
            raise SyntaxError("Parse error in JavaScript source")

        # Normalize the program
        return self._normalize_program(root)

    def normalize_node(self, node: Any) -> IRNode | list[IRNode] | None:
        """Dispatch to appropriate normalizer based on node type."""
        node_type = node.type

        # Map node types to handlers
        method_name = f"_normalize_{node_type}"
        method = getattr(self, method_name, None)

        if method is not None:
            return method(node)

        # Skip noise nodes silently
        if self._is_noise(node):
            return None

        # Warn and skip unknown nodes

        warnings.warn(
            f"JavaScript CST node type '{node_type}' not yet supported. " f"At {self._make_loc(node)}", stacklevel=2
        )
        return None

    # =========================================================================
    # Helpers
    # =========================================================================

    def _make_loc(self, node) -> SourceLocation:
        """Create SourceLocation from tree-sitter node."""
        start = node.start_point
        end = node.end_point
        return SourceLocation(
            line=start[0] + 1,  # tree-sitter is 0-indexed
            column=start[1],
            end_line=end[0] + 1,
            end_column=end[1],
            filename=self._filename,
        )

    def _get_text(self, node) -> str:
        """Get source text for a node."""
        return self._source[node.start_byte : node.end_byte]

    def _is_noise(self, node) -> bool:
        """Check if node is syntactic noise."""
        # Anonymous nodes in tree-sitter are usually punctuation/operators
        if not node.is_named:
            return True
        # Comments
        if node.type in ("comment", "line_comment", "block_comment"):
            return True
        return False

    def _find_error_node(self, node):
        """Find first ERROR node in tree."""
        if node.type == "ERROR":
            return node
        for child in node.children:
            error = self._find_error_node(child)
            if error:
                return error
        return None

    def _normalize_body(self, nodes) -> list[IRNode]:
        """Normalize a list of statement nodes."""
        result = []
        for node in nodes:
            normalized = self.normalize_node(node)
            if normalized is not None:
                if isinstance(normalized, list):
                    result.extend(normalized)
                else:
                    result.append(normalized)
        return result

    def _get_named_children(self, node) -> list:
        """Get only named (non-anonymous) children."""
        return [c for c in node.children if c.is_named]

    def _child_by_field(self, node, field: str):
        """Get child by field name, return None if not found."""
        return node.child_by_field_name(field)

    # =========================================================================
    # Program / Module
    # =========================================================================

    def _normalize_program(self, node) -> IRModule:
        """Normalize the root program node."""
        body = self._norm_body(self._get_named_children(node))

        # [20251220_BUGFIX] Cast _set_language return to IRModule
        return cast(
            IRModule,
            self._set_language(
                IRModule(
                    body=body,
                    loc=self._make_loc(node),
                )
            ),
        )

    # =========================================================================
    # Statements
    # =========================================================================

    def _normalize_expression_statement(self, node) -> IRExprStmt | None:
        """Normalize expression statement (expr;)."""
        expr_node = self._get_named_children(node)[0] if node.children else None
        if expr_node is None:
            return None

        expr = self._norm_expr(expr_node)
        if expr is None:
            return None

        return cast(
            IRExprStmt,
            self._set_language(
                IRExprStmt(
                    value=expr,
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_return_statement(self, node) -> IRReturn:
        """Normalize return statement."""
        # return; or return expr;
        # The return value is a named child, not a field
        named_children = self._get_named_children(node)
        value = self._norm_expr(named_children[0]) if named_children else None

        return cast(
            IRReturn,
            self._set_language(
                IRReturn(
                    value=value,
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_break_statement(self, node) -> IRBreak:
        """Normalize break statement."""
        return cast(IRBreak, self._set_language(IRBreak(loc=self._make_loc(node))))

    def _normalize_continue_statement(self, node) -> IRContinue:
        """Normalize continue statement."""
        return cast(IRContinue, self._set_language(IRContinue(loc=self._make_loc(node))))

    def _normalize_empty_statement(self, node) -> None:
        """Empty statement (;) - skip."""
        return None

    # =========================================================================
    # Variable Declarations
    # =========================================================================

    def _normalize_variable_declaration(self, node) -> IRAssign | list[IRAssign]:
        """
        Normalize variable declaration (const, let, var).

        CST structure:
            variable_declaration:
                "const" | "let" | "var"
                variable_declarator:
                    name: identifier
                    value: expression (optional)
        """
        declarators = [c for c in node.children if c.type == "variable_declarator"]

        if len(declarators) == 1:
            return self._normalize_variable_declarator(declarators[0])

        # Multiple declarations: const a = 1, b = 2;
        return [self._normalize_variable_declarator(d) for d in declarators]

    def _normalize_variable_declarator(self, node) -> IRAssign:
        """Normalize single variable declarator."""
        name_node = self._child_by_field(node, "name")
        value_node = self._child_by_field(node, "value")

        target = self._norm_expr(name_node) if name_node else None
        value = self._norm_expr(value_node) if value_node else IRConstant(value=None)

        return cast(
            IRAssign,
            self._set_language(
                IRAssign(
                    targets=[cast(IRExpr, target)] if target else [],
                    value=value,
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_lexical_declaration(self, node) -> IRAssign | list[IRAssign]:
        """Normalize lexical declaration (let, const in ES6)."""
        return self._normalize_variable_declaration(node)

    # =========================================================================
    # Functions
    # =========================================================================

    def _normalize_function_declaration(self, node) -> IRFunctionDef:
        """
        Normalize function declaration.

        CST structure:
            function_declaration:
                "async"? (optional)
                "function"
                name: identifier
                parameters: formal_parameters
                body: statement_block
        """
        name_node = self._child_by_field(node, "name")
        params_node = self._child_by_field(node, "parameters")
        body_node = self._child_by_field(node, "body")

        name = self._get_text(name_node) if name_node else ""
        params = self._normalize_parameters(params_node) if params_node else []
        body = self._normalize_block(body_node) if body_node else []

        # Check for async keyword
        is_async = any(c.type == "async" or self._get_text(c) == "async" for c in node.children if not c.is_named)

        return cast(
            IRFunctionDef,
            self._set_language(
                IRFunctionDef(
                    name=name,
                    params=params,
                    body=body,
                    is_async=is_async,
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_arrow_function(self, node) -> IRFunctionDef:
        """
        Normalize arrow function.

        CST structure:
            arrow_function:
                "async"? (optional)
                parameter: identifier | formal_parameters
                "=>"
                body: expression | statement_block
        """
        param_node = self._child_by_field(node, "parameter")
        params_node = self._child_by_field(node, "parameters")
        body_node = self._child_by_field(node, "body")

        # Parameters can be single identifier or formal_parameters
        if param_node:
            params = [IRParameter(name=self._get_text(param_node))]
        elif params_node:
            params = self._normalize_parameters(params_node)
        else:
            params = []

        # Body can be expression or block
        if body_node:
            if body_node.type == "statement_block":
                body = self._normalize_block(body_node)
            else:
                # Expression body: implicit return
                expr = self._norm_expr(body_node)
                body = [IRReturn(value=expr)] if expr else []
        else:
            body = []

        is_async = any(c.type == "async" or self._get_text(c) == "async" for c in node.children if not c.is_named)

        return cast(
            IRFunctionDef,
            self._set_language(
                IRFunctionDef(
                    name="",  # Arrow functions are anonymous
                    params=params,
                    body=cast(list[IRNode], body),
                    is_async=is_async,
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_function_expression(self, node) -> IRFunctionDef:
        """Normalize function expression (anonymous or named)."""
        return self._normalize_function_declaration(node)

    def _normalize_generator_function_declaration(self, node) -> IRFunctionDef:
        """Normalize generator function declaration."""
        func = self._normalize_function_declaration(node)
        func.is_generator = True
        return func

    def _normalize_parameters(self, node) -> list[IRParameter]:
        """Normalize formal parameters."""
        params = []
        for child in self._get_named_children(node):
            if child.type == "identifier":
                params.append(IRParameter(name=self._get_text(child)))
            elif child.type == "assignment_pattern":
                # Default parameter: a = 1
                name_node = self._child_by_field(child, "left")
                default_node = self._child_by_field(child, "right")
                params.append(
                    IRParameter(
                        name=self._get_text(name_node) if name_node else "",
                        default=(self._norm_expr(default_node) if default_node else None),
                    )
                )
            elif child.type == "rest_pattern":
                # Rest parameter: ...args
                name_node = child.children[1] if len(child.children) > 1 else None
                params.append(
                    IRParameter(
                        name=self._get_text(name_node) if name_node else "",
                        is_rest=True,  # [20251220_BUGFIX] Correct parameter name
                    )
                )
        return params

    def _normalize_statement_block(self, node) -> list[IRNode]:
        """Normalize statement block ({ ... })."""
        return self._normalize_block(node)

    def _normalize_block(self, node) -> list[IRNode]:
        """Normalize a block of statements."""
        return self._normalize_body(self._get_named_children(node))

    # =========================================================================
    # Control Flow
    # =========================================================================

    def _normalize_if_statement(self, node) -> IRIf:
        """
        Normalize if statement.

        CST structure:
            if_statement:
                "if"
                condition: parenthesized_expression
                consequence: statement
                "else"? (optional)
                alternative: statement (optional)
        """
        cond_node = self._child_by_field(node, "condition")
        cons_node = self._child_by_field(node, "consequence")
        alt_node = self._child_by_field(node, "alternative")

        # Condition is wrapped in parentheses, unwrap it
        condition = self._unwrap_expression(cond_node) if cond_node else None

        # Consequence
        if cons_node:
            if cons_node.type == "statement_block":
                consequence = self._normalize_block(cons_node)
            else:
                cons = self.normalize_node(cons_node)
                consequence = [cons] if cons else []
        else:
            consequence = []

        # Alternative (else branch)
        alternative = []
        if alt_node:
            if alt_node.type == "statement_block":
                alternative = self._normalize_block(alt_node)
            elif alt_node.type == "if_statement":
                # else if -> nested if
                alternative = [self._normalize_if_statement(alt_node)]
            else:
                alt = self.normalize_node(alt_node)
                alternative = [alt] if alt else []

        return cast(
            IRIf,
            self._set_language(
                IRIf(
                    test=condition,
                    body=cast(list[IRNode], consequence),
                    orelse=cast(list[IRNode], alternative),
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_while_statement(self, node) -> IRWhile:
        """Normalize while statement."""
        cond_node = self._child_by_field(node, "condition")
        body_node = self._child_by_field(node, "body")

        condition = self._unwrap_expression(cond_node) if cond_node else None

        if body_node:
            if body_node.type == "statement_block":
                body = self._normalize_block(body_node)
            else:
                stmt = self.normalize_node(body_node)
                body = [stmt] if stmt else []
        else:
            body = []

        return cast(
            IRWhile,
            self._set_language(
                IRWhile(
                    test=condition,
                    body=cast(list[IRNode], body),
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_for_statement(self, node) -> IRFor:
        """
        Normalize for statement.

        CST: for (init; condition; update) body
        IR: For loop with init, test, update, body
        """
        init_node = self._child_by_field(node, "initializer")
        cond_node = self._child_by_field(node, "condition")
        update_node = self._child_by_field(node, "update")
        body_node = self._child_by_field(node, "body")

        # For traditional for loops, we'll model as IRFor
        # Target is the loop variable (from init)
        # Iter is a synthetic range (or update expression)

        init = self.normalize_node(init_node) if init_node else None
        condition = self.normalize_node(cond_node) if cond_node else None
        update = self.normalize_node(update_node) if update_node else None

        if body_node:
            if body_node.type == "statement_block":
                body = self._normalize_block(body_node)
            else:
                stmt = self.normalize_node(body_node)
                body = [stmt] if stmt else []
        else:
            body = []

        # Traditional for loops don't map cleanly to IR for-each
        # We'll use IRWhile as the best approximation

        # For now, return as IRWhile with init prepended
        while_node = IRWhile(
            test=cast(IRExpr | None, condition if condition else IRConstant(value=True)),
            body=cast(
                list[IRNode],
                body + ([IRExprStmt(value=cast(IRExpr | None, update))] if update else []),
            ),
            loc=self._make_loc(node),
        )

        if init:
            # Return list: init statement + while loop
            if isinstance(init, list):
                return cast(IRFor, init + [self._set_language(while_node)])
            return cast(IRFor, [init, self._set_language(while_node)])

        return cast(IRFor, self._set_language(while_node))

    def _normalize_for_in_statement(self, node) -> IRFor:
        """Normalize for-in statement (for (x in obj))."""
        left_node = self._child_by_field(node, "left")
        right_node = self._child_by_field(node, "right")
        body_node = self._child_by_field(node, "body")

        # Left can be variable declaration or identifier
        if left_node:
            if left_node.type in ("variable_declaration", "lexical_declaration"):
                declarator = [c for c in left_node.children if c.type == "variable_declarator"][0]
                name_node = self._child_by_field(declarator, "name")
                # [20251214_BUGFIX] IRName constructor uses 'id' rather than 'name'.
                target = IRName(id=self._get_text(name_node)) if name_node else None
            else:
                target = self._norm_expr(left_node)
        else:
            target = None

        iter_expr = self._norm_expr(right_node) if right_node else None

        if body_node:
            if body_node.type == "statement_block":
                body = self._normalize_block(body_node)
            else:
                stmt = self.normalize_node(body_node)
                body = [stmt] if stmt else []
        else:
            body = []

        return cast(
            IRFor,
            self._set_language(
                IRFor(
                    target=target,
                    iter=iter_expr,
                    body=cast(list[IRNode], body),
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_for_of_statement(self, node) -> IRFor:
        """Normalize for-of statement (for (x of iterable))."""
        # Same structure as for-in
        return self._normalize_for_in_statement(node)

    # =========================================================================
    # Expressions
    # =========================================================================

    def _unwrap_expression(self, node) -> IRExpr | None:
        """Unwrap parenthesized expression if needed."""
        if node.type == "parenthesized_expression":
            inner = self._get_named_children(node)
            if inner:
                result = self.normalize_node(inner[0])
                return cast(IRExpr, result) if not isinstance(result, list) else None
        result = self.normalize_node(node)
        return cast(IRExpr, result) if not isinstance(result, list) else None

    def _normalize_parenthesized_expression(self, node) -> IRExpr | None:
        """Normalize parenthesized expression."""
        inner = self._get_named_children(node)
        if inner:
            result = self.normalize_node(inner[0])
            return cast(IRExpr, result) if not isinstance(result, list) else None
        return None

    def _normalize_binary_expression(self, node) -> IRBinaryOp | IRCompare | IRBoolOp:
        """
        Normalize binary expression.

        CST structure:
            binary_expression:
                left: expression
                operator (anonymous)
                right: expression

            - Optional chaining edge cases: obj?.prop?.method?.()
            - Nullish coalescing combinations: a ?? b ?? c
            - Spread operator normalization: ...arr, ...obj
            - Rest parameters in function calls
            - Exponentiation operator: ** (already supported)

            - Promise chain tracking across statements
            - Async IIFE detection and handling
            - Top-level await in modules
            - Error boundary patterns with try/catch

            - import() expressions as special function calls
            - Metadata preservation for lazy loading patterns
            - Conditional imports detection
        """
        left_node = self._child_by_field(node, "left")
        right_node = self._child_by_field(node, "right")

        # Find operator (anonymous node between left and right)
        op_text = None
        for child in node.children:
            if not child.is_named:
                text = self._get_text(child).strip()
                if text:
                    op_text = text
                    break

        left = self._norm_expr(left_node) if left_node else None
        right = self._norm_expr(right_node) if right_node else None
        loc = self._make_loc(node)

        # Determine operator type
        if op_text in BINARY_OP_MAP:
            return cast(
                IRBinaryOp,
                self._set_language(
                    IRBinaryOp(
                        op=BINARY_OP_MAP[op_text],
                        left=left,
                        right=right,
                        loc=loc,
                    )
                ),
            )
        elif op_text in COMPARE_OP_MAP:
            return cast(
                IRBinaryOp,
                self._set_language(
                    IRCompare(
                        ops=[COMPARE_OP_MAP[op_text]],
                        left=left,
                        comparators=[cast(IRExpr, right)] if right else [],
                        loc=loc,
                    )
                ),
            )
        elif op_text in BOOL_OP_MAP:
            return cast(
                IRBinaryOp,
                self._set_language(
                    IRBoolOp(
                        op=BOOL_OP_MAP[op_text],
                        values=[cast(IRExpr, v) for v in [left, right] if v],
                        loc=loc,
                    )
                ),
            )
        else:
            import warnings

            warnings.warn(f"Unknown binary operator '{op_text}' at {loc}", stacklevel=2)
            # Return as binary op with ADD as placeholder
            return cast(
                IRBinaryOp,
                self._set_language(
                    IRBinaryOp(
                        op=BinaryOperator.ADD,
                        left=left,
                        right=right,
                        loc=loc,
                    )
                ),
            )

    def _normalize_unary_expression(self, node) -> IRUnaryOp:
        """Normalize unary expression."""
        arg_node = self._child_by_field(node, "argument")

        # Find operator
        op_text = None
        for child in node.children:
            if not child.is_named:
                text = self._get_text(child).strip()
                if text and text != "(":
                    op_text = text
                    break

        operand = self._norm_expr(arg_node) if arg_node else None
        op = UNARY_OP_MAP.get(op_text or "", UnaryOperator.NEG)  # [20251220_BUGFIX] Guard None op_text

        return cast(
            IRUnaryOp,
            self._set_language(
                IRUnaryOp(
                    op=op,
                    operand=operand,
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_update_expression(self, node) -> IRAugAssign:
        """Normalize update expression (++x, x++, --x, x--)."""
        arg_node = self._child_by_field(node, "argument")

        # Find operator
        op_text = None
        for child in node.children:
            if not child.is_named:
                text = self._get_text(child).strip()
                if text in ("++", "--"):
                    op_text = text
                    break

        target = self._norm_expr(arg_node) if arg_node else None
        op = AugAssignOperator.ADD if op_text == "++" else AugAssignOperator.SUB

        return cast(
            IRAugAssign,
            self._set_language(
                IRAugAssign(
                    target=target,
                    op=op,
                    value=IRConstant(value=1),
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_assignment_expression(self, node) -> IRAssign:
        """Normalize assignment expression."""
        left_node = self._child_by_field(node, "left")
        right_node = self._child_by_field(node, "right")

        target = self._norm_expr(left_node) if left_node else None
        value = self._norm_expr(right_node) if right_node else None

        return cast(
            IRAssign,
            self._set_language(
                IRAssign(
                    targets=[cast(IRExpr, target)] if target else [],
                    value=value,
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_augmented_assignment_expression(self, node) -> IRAugAssign:
        """Normalize augmented assignment (+=, -=, etc.)."""
        left_node = self._child_by_field(node, "left")
        right_node = self._child_by_field(node, "right")

        # Find operator
        op_text = None
        for child in node.children:
            if not child.is_named:
                text = self._get_text(child).strip()
                if text in AUG_ASSIGN_OP_MAP:
                    op_text = text
                    break

        target = self._norm_expr(left_node) if left_node else None
        value = self._norm_expr(right_node) if right_node else None
        op = AUG_ASSIGN_OP_MAP.get(op_text or "", AugAssignOperator.ADD)

        return cast(
            IRAugAssign,
            self._set_language(
                IRAugAssign(
                    target=target,
                    op=op,
                    value=value,
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_call_expression(self, node) -> IRCall:
        """Normalize function call."""
        func_node = self._child_by_field(node, "function")
        args_node = self._child_by_field(node, "arguments")

        func = self._norm_expr(func_node) if func_node else None

        args = []
        if args_node:
            for arg in self._get_named_children(args_node):
                arg_ir = self._norm_expr(arg)
                if arg_ir:
                    args.append(arg_ir)

        return cast(
            IRCall,
            self._set_language(
                IRCall(
                    func=func,
                    args=args,
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_new_expression(self, node) -> IRCall:
        """[20251215_FEATURE] Best-effort normalization for `new Foo()` expressions."""
        ctor_node = self._child_by_field(node, "constructor") or None
        args_node = self._child_by_field(node, "arguments")

        ctor = self._norm_expr(ctor_node) if ctor_node else IRName(id="")

        args: list[IRExpr] = []
        if args_node:
            for arg in self._get_named_children(args_node):
                normalized = self._norm_expr(arg)
                if normalized is not None:
                    args.append(normalized)

        call = IRCall(
            func=ctor,
            args=args,
            loc=self._make_loc(node),
        )
        call._metadata["is_new"] = True
        return cast(IRCall, self._set_language(call))

    def _normalize_await_expression(self, node) -> IRCall:
        """[20251215_FEATURE] Represent `await expr` as a call-like IR node for downstream handling."""
        arg_node = self._child_by_field(node, "argument") or None
        arg_ir = self._norm_expr(arg_node) if arg_node else None

        call = IRCall(
            func=IRName(id="await"),
            args=[arg_ir] if arg_ir else [],
            loc=self._make_loc(node),
        )
        call._metadata["is_await"] = True
        return cast(IRCall, self._set_language(call))

    def _normalize_as_expression(self, node) -> IRExpr | None:
        """[20251215_FEATURE] TypeScript `as` assertions return the underlying expression."""
        expr_node = self._child_by_field(node, "expression")
        if expr_node is None:
            named = self._get_named_children(node)
            expr_node = named[0] if named else None
        return self._norm_expr(expr_node) if expr_node else None

    def _normalize_satisfies_expression(self, node) -> IRExpr | None:
        """[20251215_FEATURE] TypeScript `satisfies` assertions are erased to the expression value."""
        expr_node = self._child_by_field(node, "left")
        if expr_node is None:
            named = self._get_named_children(node)
            expr_node = named[0] if named else None
        return self._norm_expr(expr_node) if expr_node else None

    def _normalize_member_expression(self, node) -> IRAttribute | IRSubscript:
        """Normalize member access (obj.prop or obj[key])."""
        obj_node = self._child_by_field(node, "object")
        prop_node = self._child_by_field(node, "property")

        obj = self._norm_expr(obj_node) if obj_node else None

        # Check if bracket notation (computed)
        is_computed = any(self._get_text(c) == "[" for c in node.children if not c.is_named)

        if is_computed and prop_node:
            # obj[key] -> IRSubscript
            key = self._norm_expr(prop_node)
            return cast(
                IRSubscript,
                self._set_language(
                    IRSubscript(
                        value=obj,
                        slice=key,
                        loc=self._make_loc(node),
                    )
                ),
            )
        else:
            # obj.prop -> IRAttribute
            attr = self._get_text(prop_node) if prop_node else ""
            return cast(
                IRAttribute,
                self._set_language(
                    IRAttribute(
                        value=obj,
                        attr=attr,
                        loc=self._make_loc(node),
                    )
                ),
            )

    def _normalize_subscript_expression(self, node) -> IRSubscript:
        """Normalize subscript access (obj[key])."""
        obj_node = self._child_by_field(node, "object")
        index_node = self._child_by_field(node, "index")

        # Normalize nodes directly to get IRExpr objects
        obj = self._norm_expr(obj_node) if obj_node else None
        index = self._norm_expr(index_node) if index_node else None

        return cast(
            IRSubscript,
            self._set_language(
                IRSubscript(
                    value=obj,
                    slice=index,
                    loc=self._make_loc(node),
                )
            ),
        )

    # =========================================================================
    # Literals / Atoms
    # =========================================================================

    def _normalize_identifier(self, node) -> IRName:
        """Normalize identifier."""
        return cast(
            IRName,
            self._set_language(
                IRName(
                    id=self._get_text(node),
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_this(self, node) -> IRName:
        """[20251215_FEATURE] Normalize `this` reference as an identifier."""
        return cast(
            IRName,
            self._set_language(
                IRName(
                    id="this",
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_property_identifier(self, node) -> IRName:
        """Normalize property identifier (in member expressions)."""
        return self._normalize_identifier(node)

    def _normalize_number(self, node) -> IRConstant:
        """Normalize number literal."""
        text = self._get_text(node)
        try:
            if "." in text or "e" in text.lower():
                value = float(text)
            else:
                value = int(text, 0)  # Auto-detect base (0x, 0o, 0b)
        except ValueError:
            value = float(text)

        return cast(
            IRConstant,
            self._set_language(
                IRConstant(
                    value=value,
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_string(self, node) -> IRConstant:
        """Normalize string literal."""
        text = self._get_text(node)
        # Remove quotes
        if text.startswith(('"""', "'''")):
            value = text[3:-3]
        elif text.startswith(('"', "'")):
            value = text[1:-1]
        else:
            value = text

        return cast(
            IRConstant,
            self._set_language(
                IRConstant(
                    value=value,
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_template_string(self, node) -> IRConstant:
        """Normalize template string (`...`)."""
        text = self._get_text(node)
        # For now, treat as plain string
        value = text[1:-1] if text.startswith("`") else text

        return cast(
            IRConstant,
            self._set_language(
                IRConstant(
                    value=value,
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_jsx_element(self, node) -> IRConstant:
        """[20251215_FEATURE] Represent JSX elements as opaque constants to avoid warnings."""
        raw = self._get_text(node)
        return cast(
            IRConstant,
            self._set_language(
                IRConstant(
                    value=raw,
                    raw=raw,
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_jsx_self_closing_element(self, node) -> IRConstant:
        """[20251215_FEATURE] Represent self-closing JSX elements as opaque constants."""
        raw = self._get_text(node)
        return cast(
            IRConstant,
            self._set_language(
                IRConstant(
                    value=raw,
                    raw=raw,
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_jsx_fragment(self, node) -> IRConstant:
        """[20251215_FEATURE] Represent JSX fragments as opaque constants."""
        raw = self._get_text(node)
        return cast(
            IRConstant,
            self._set_language(
                IRConstant(
                    value=raw,
                    raw=raw,
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_true(self, node) -> IRConstant:
        """Normalize true literal."""
        return cast(
            IRConstant,
            self._set_language(IRConstant(value=True, loc=self._make_loc(node))),
        )

    def _normalize_false(self, node) -> IRConstant:
        """Normalize false literal."""
        return cast(
            IRConstant,
            self._set_language(IRConstant(value=False, loc=self._make_loc(node))),
        )

    def _normalize_null(self, node) -> IRConstant:
        """Normalize null literal."""
        return cast(
            IRConstant,
            self._set_language(IRConstant(value=None, loc=self._make_loc(node))),
        )

    def _normalize_undefined(self, node) -> IRConstant:
        """Normalize undefined literal."""
        return cast(
            IRConstant,
            self._set_language(IRConstant(value=None, loc=self._make_loc(node))),
        )

    def _normalize_array(self, node) -> IRList:
        """Normalize array literal."""
        elements = []
        for child in self._get_named_children(node):
            elem = self.normalize_node(child)
            if elem:
                elements.append(elem)

        # [20251214_BUGFIX] IRList expects 'elements', not legacy 'elts' keyword.
        return cast(
            IRList,
            self._set_language(
                IRList(
                    elements=elements,
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_array_pattern(self, node) -> IRList:
        """[20251215_FEATURE] Normalize destructuring patterns as IRList targets."""
        elements = []
        for child in self._get_named_children(node):
            normalized = self.normalize_node(child)
            if normalized is not None:
                elements.append(normalized)

        return cast(
            IRList,
            self._set_language(
                IRList(
                    elements=elements,
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_object(self, node) -> IRDict:
        """Normalize object literal."""
        keys = []
        values = []

        for child in self._get_named_children(node):
            if child.type == "pair":
                key_node = self._child_by_field(child, "key")
                value_node = self._child_by_field(child, "value")

                if key_node:
                    key_text = self._get_text(key_node)
                    # Key can be identifier or string
                    if key_node.type == "string":
                        key_text = key_text[1:-1]  # Remove quotes
                    keys.append(IRConstant(value=key_text))

                if value_node:
                    values.append(self.normalize_node(value_node))
            elif child.type == "shorthand_property_identifier":
                # { foo } -> { foo: foo }
                name = self._get_text(child)
                keys.append(IRConstant(value=name))
                # [20251214_BUGFIX] Align IRName construction with dataclass field 'id'.
                values.append(IRName(id=name))

        return cast(
            IRDict,
            self._set_language(
                IRDict(
                    keys=keys,
                    values=values,
                    loc=self._make_loc(node),
                )
            ),
        )

    # =========================================================================
    # Classes
    # =========================================================================

    def _normalize_class_declaration(self, node) -> IRClassDef:
        """Normalize class declaration."""
        name_node = self._child_by_field(node, "name")
        heritage_node = self._child_by_field(node, "heritage")  # extends
        body_node = self._child_by_field(node, "body")

        name = self._get_text(name_node) if name_node else ""

        # Extract base class from heritage clause
        bases = []
        if heritage_node:
            for child in self._get_named_children(heritage_node):
                base = self.normalize_node(child)
                if base:
                    bases.append(base)

        # Normalize class body
        body = []
        if body_node:
            for member in self._get_named_children(body_node):
                normalized = self.normalize_node(member)
                if normalized:
                    if isinstance(normalized, list):
                        body.extend(normalized)
                    else:
                        body.append(normalized)

        return cast(
            IRClassDef,
            self._set_language(
                IRClassDef(
                    name=name,
                    bases=bases,
                    body=body,
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_class(self, node) -> IRClassDef:
        """[20251215_FEATURE] Alias handler for class nodes emitted by TS/JSX grammars."""
        return self._normalize_class_declaration(node)

    def _normalize_public_field_definition(self, node) -> IRAssign:
        """[20251215_FEATURE] Handle class public field declarations."""
        name_node = self._child_by_field(node, "name")
        if name_node is None:
            named = self._get_named_children(node)
            name_node = named[0] if named else None

        value_node = self._child_by_field(node, "value")
        field_name = self._get_text(name_node) if name_node else ""
        target = IRAttribute(value=IRName(id="this"), attr=field_name)
        value_result = (
            self.normalize_node(value_node) if value_node is not None else IRConstant(value=None, raw="undefined")
        )
        value = (
            cast(IRExpr, value_result)
            if not isinstance(value_result, list)
            else IRConstant(value=None, raw="undefined")
        )

        return cast(
            IRAssign,
            self._set_language(
                IRAssign(
                    targets=[cast(IRExpr, target)] if target else [],
                    value=value,
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_class_body(self, node) -> list[IRNode]:
        """Normalize class body."""
        return self._normalize_body(self._get_named_children(node))

    def _normalize_method_definition(self, node) -> IRFunctionDef:
        """Normalize class method definition."""
        name_node = self._child_by_field(node, "name")
        params_node = self._child_by_field(node, "parameters")
        body_node = self._child_by_field(node, "body")

        name = self._get_text(name_node) if name_node else ""
        params = self._normalize_parameters(params_node) if params_node else []
        body = self._normalize_block(body_node) if body_node else []

        # Check for async, static, get, set keywords
        is_async = any(self._get_text(c) == "async" for c in node.children if not c.is_named)

        return cast(
            IRFunctionDef,
            self._set_language(
                IRFunctionDef(
                    name=name,
                    params=params,
                    body=body,
                    is_async=is_async,
                    loc=self._make_loc(node),
                )
            ),
        )

    # =========================================================================
    # Try/Catch/Finally - [20251215_FEATURE] v2.0.0 - IRTry now implemented
    # =========================================================================

    def _normalize_try_statement(self, node) -> IRTry:
        """
        Normalize try statement.

        [20251215_FEATURE] v2.0.0 - Full try/catch/finally support.

        CST structure:
            try_statement:
                body: statement_block
                handler: catch_clause (optional)
                finalizer: finally_clause (optional)
        """
        body_node = self._child_by_field(node, "body")
        handler_node = self._child_by_field(node, "handler")
        finalizer_node = self._child_by_field(node, "finalizer")

        body = self._normalize_block(body_node) if body_node else []

        handlers = []
        if handler_node:
            # catch_clause has optional parameter and body
            param_node = self._child_by_field(handler_node, "parameter")
            catch_body_node = self._child_by_field(handler_node, "body")

            param_name = self._get_text(param_node) if param_node else None
            catch_body = self._normalize_block(catch_body_node) if catch_body_node else []

            # (exception_type, name, body) - JS doesn't have typed exceptions
            handlers.append((None, param_name, catch_body))

        finalbody = []
        if finalizer_node:
            # finally_clause just has body
            finally_body_node = self._child_by_field(finalizer_node, "body")
            finalbody = self._normalize_block(finally_body_node) if finally_body_node else []

        return cast(
            IRTry,
            self._set_language(
                IRTry(
                    body=body,
                    handlers=handlers,
                    orelse=[],  # JS doesn't have try-else
                    finalbody=finalbody,
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_throw_statement(self, node) -> IRRaise:
        """
        Normalize throw statement.

        [20251215_FEATURE] v2.0.0 - IRRaise support.

        CST structure:
            throw_statement:
                expression
        """
        named_children = self._get_named_children(node)
        exc_node = self.normalize_node(named_children[0]) if named_children else None
        exc = cast(IRExpr, exc_node) if exc_node and not isinstance(exc_node, list) else None

        return cast(
            IRRaise,
            self._set_language(
                IRRaise(
                    exc=exc,
                    cause=None,  # JS doesn't have 'from' clause
                    loc=self._make_loc(node),
                )
            ),
        )

    # =========================================================================
    # Import/Export - [20251215_FEATURE] v2.0.0 - ES6 module support
    # =========================================================================

    def _normalize_import_statement(self, node) -> IRImport:
        """
        Normalize ES6 import statement.

        CST examples:
            import foo from 'foo'           -> default import
            import { bar } from 'foo'       -> named import
            import { bar as baz } from 'foo' -> aliased import
            import * as foo from 'foo'      -> namespace import
            import 'foo'                    -> side-effect import
        """
        source_node = self._child_by_field(node, "source")
        module = ""
        if source_node:
            module = self._get_text(source_node).strip("'\"")

        names = []
        alias = None
        is_default = False
        is_star = False

        for child in node.children:
            if child.type == "import_clause":
                # Process import clause
                for clause_child in child.children:
                    if clause_child.type == "identifier":
                        # Default import: import foo from 'foo'
                        is_default = True
                        names.append(self._get_text(clause_child))
                    elif clause_child.type == "namespace_import":
                        # import * as foo from 'foo'
                        is_star = True
                        alias_node = self._child_by_field(clause_child, "alias")
                        if alias_node:
                            alias = self._get_text(alias_node)
                    elif clause_child.type == "named_imports":
                        # import { bar, baz } from 'foo'
                        for spec in self._get_named_children(clause_child):
                            if spec.type == "import_specifier":
                                name_node = self._child_by_field(spec, "name")
                                alias_node = self._child_by_field(spec, "alias")
                                if name_node:
                                    names.append(self._get_text(name_node))
                                    if alias_node:
                                        alias = self._get_text(alias_node)

        return cast(
            IRImport,
            self._set_language(
                IRImport(
                    module=module,
                    names=names,
                    alias=alias,
                    is_default=is_default,
                    is_star=is_star,
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_export_statement(self, node) -> IRExport:
        """
        Normalize ES6 export statement.

        CST examples:
            export default function() {}
            export { foo, bar }
            export const x = 1
            export { x } from 'y'
        """
        names = []
        declaration = None
        is_default = False
        source = None

        for child in node.children:
            if not child.is_named:
                text = self._get_text(child)
                if text == "default":
                    is_default = True
            elif child.type == "export_clause":
                # export { foo, bar }
                for spec in self._get_named_children(child):
                    if spec.type == "export_specifier":
                        name_node = self._child_by_field(spec, "name")
                        if name_node:
                            names.append(self._get_text(name_node))
            elif child.type == "string":
                # Re-export source: export { x } from 'y'
                source = self._get_text(child).strip("'\"")
            elif child.type in (
                "function_declaration",
                "class_declaration",
                "lexical_declaration",
                "variable_declaration",
            ):
                # export const x = 1, export function foo() {}
                decl_node = self.normalize_node(child)
                declaration = decl_node if not isinstance(decl_node, list) else None

        return cast(
            IRExport,
            self._set_language(
                IRExport(
                    names=names,
                    declaration=declaration,
                    is_default=is_default,
                    source=source,
                    loc=self._make_loc(node),
                )
            ),
        )

    # =========================================================================
    # Switch Statement - [20251215_FEATURE] v2.0.0
    # =========================================================================

    def _normalize_switch_statement(self, node) -> IRSwitch:
        """
        Normalize switch statement.

        CST structure:
            switch_statement:
                value: parenthesized_expression
                body: switch_body
        """
        value_node = self._child_by_field(node, "value")
        body_node = self._child_by_field(node, "body")

        discriminant = self._unwrap_expression(value_node) if value_node else None

        cases = []
        if body_node:
            for child in self._get_named_children(body_node):
                if child.type == "switch_case":
                    # case x: ...
                    test_node = self._child_by_field(child, "value")
                    test = self.normalize_node(test_node) if test_node else None
                    body = self._normalize_case_body(child)
                    cases.append((test, body))
                elif child.type == "switch_default":
                    # default: ...
                    body = self._normalize_case_body(child)
                    cases.append((None, body))

        return cast(
            IRSwitch,
            self._set_language(
                IRSwitch(
                    discriminant=discriminant,
                    cases=cases,
                    loc=self._make_loc(node),
                )
            ),
        )

    def _normalize_case_body(self, node) -> list[IRNode]:
        """Extract statements from a switch case/default."""
        body = []
        for child in self._get_named_children(node):
            # Skip the case value node
            if child.type not in ("number", "string", "identifier"):
                normalized = self.normalize_node(child)
                if normalized:
                    if isinstance(normalized, list):
                        body.extend(normalized)
                    else:
                        body.append(normalized)
        return body

    # =========================================================================
    # Ternary Expression - [20251215_FEATURE] v2.0.0
    # =========================================================================

    def _normalize_ternary_expression(self, node) -> IRTernary:
        """
        Normalize ternary/conditional expression (condition ? true : false).

        CST structure:
            ternary_expression:
                condition: expression
                consequence: expression
                alternative: expression
        """
        cond_node = self._child_by_field(node, "condition")
        cons_node = self._child_by_field(node, "consequence")
        alt_node = self._child_by_field(node, "alternative")

        test_node = self.normalize_node(cond_node) if cond_node else None
        body_node = self.normalize_node(cons_node) if cons_node else None
        orelse_node = self.normalize_node(alt_node) if alt_node else None

        test = cast(IRExpr, test_node) if test_node and not isinstance(test_node, list) else None
        body = cast(IRExpr, body_node) if body_node and not isinstance(body_node, list) else None
        orelse = cast(IRExpr, orelse_node) if orelse_node and not isinstance(orelse_node, list) else None

        return cast(
            IRTernary,
            self._set_language(
                IRTernary(
                    test=test,
                    body=body,
                    orelse=orelse,
                    loc=self._make_loc(node),
                )
            ),
        )

    # Alias for common tree-sitter name
    _normalize_conditional_expression = _normalize_ternary_expression
