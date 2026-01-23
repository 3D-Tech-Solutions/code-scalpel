"""
Python Normalizer - Convert Python ast.* to Unified IR.

This normalizer provides a 1:1 mapping from Python's ast module
to the Unified IR. It serves as the reference implementation.

Python's ast module produces an Abstract Syntax Tree, which maps
cleanly to our IR without needing to filter "noise" nodes.
"""

from __future__ import annotations

import ast
from typing import cast

from ..nodes import (
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
    IRExpr,
    IRExprStmt,
    IRFor,
    IRFunctionDef,
    IRIf,
    IRList,
    IRModule,
    IRName,
    IRNode,
    IRParameter,
    IRPass,
    IRRaise,
    IRReturn,
    IRSubscript,
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


class PythonNormalizer(BaseNormalizer):
    """
    Normalizes Python ast.* nodes to Unified IR.

    This is a straightforward mapping since Python's ast is already abstract.
    The main work is converting Python-specific node types to IR node types.

    Example:
        >>> normalizer = PythonNormalizer()
        >>> ir = normalizer.normalize('''
        ... def add(a, b):
        ...     return a + b
        ... ''')
        >>> ir.body[0].name
        'add'


    COMMUNITY TIER (Core Python AST Normalization):

    PRO TIER (Advanced Python Features):

    ENTERPRISE TIER (Advanced Analysis & Optimization):
    """

    def __init__(self):
        self._filename: str = "<string>"

    @property
    def language(self) -> str:
        return "python"

    def normalize(self, source: str, filename: str = "<string>") -> IRModule:
        """Parse Python source and normalize to IR."""
        self._filename = filename

        try:
            tree = ast.parse(source, filename=filename)
        except SyntaxError:
            raise

        return self._normalize_Module(tree)

    def normalize_node(self, node: ast.AST) -> IRNode | list[IRNode] | None:
        """Dispatch to appropriate normalizer based on node type."""
        method_name = f"_normalize_{node.__class__.__name__}"
        method = getattr(self, method_name, None)

        if method is None:
            raise NotImplementedError(
                f"Python AST node type '{node.__class__.__name__}' " f"is not yet supported in IR normalization"
            )

        return method(node)

    # =========================================================================
    # Helpers
    # =========================================================================

    def _make_loc(self, node: ast.AST) -> SourceLocation | None:
        """Extract source location from ast node."""
        # [20251220_BUGFIX] hasattr check handles AST nodes safely regardless of attributes
        if not hasattr(node, "lineno"):
            return None

        # Safe access - we verified lineno exists
        lineno = getattr(node, "lineno", 0)
        return SourceLocation(
            line=lineno,
            column=getattr(node, "col_offset", 0),
            end_line=getattr(node, "end_lineno", None),
            end_column=getattr(node, "end_col_offset", None),
            filename=self._filename,
        )

    def _norm_expr(self, node: ast.AST | None) -> IRExpr | None:
        """
        [20251220_BUGFIX] Normalize node to IRExpr with type casting.

        Converts Union[IRNode, List[IRNode], None] to IRExpr | None
        for expression contexts.
        """
        if node is None:
            return None
        result = self.normalize_node(node)
        # Cast to IRExpr - caller ensures node is expression-like
        return cast(IRExpr, result) if not isinstance(result, list) else None

    def _norm_expr_list(self, nodes: list[ast.expr]) -> list[IRExpr]:
        """
        [20251220_BUGFIX] Normalize list of expression nodes to List[IRExpr] with type casting.
        """
        results = []
        for node in nodes:
            result = self.normalize_node(node)
            if not isinstance(result, list) and result is not None:
                results.append(cast(IRExpr, result))
        return results

    def _normalize_body(self, body: list[ast.stmt]) -> list[IRNode]:
        """Normalize a list of statements."""
        result = []
        for stmt in body:
            normalized = self.normalize_node(stmt)
            if normalized is not None:
                if isinstance(normalized, list):
                    result.extend(normalized)
                else:
                    result.append(normalized)
        return result

    # =========================================================================
    # Module
    # =========================================================================

    def _normalize_Module(self, node: ast.Module) -> IRModule:
        """Normalize module (root node)."""
        # Extract docstring if present
        docstring = None
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            docstring = node.body[0].value.value

        return IRModule(
            body=self._normalize_body(node.body),
            docstring=docstring,
            loc=None,
            source_language=self.language,
        )

    # =========================================================================
    # Statements
    # =========================================================================

    def _normalize_FunctionDef(self, node: ast.FunctionDef) -> IRFunctionDef:
        """Normalize function definition."""
        # Extract docstring
        docstring = None
        body = node.body
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            docstring = body[0].value.value

        # [20251220_BUGFIX] Cast decorator list and normalize to IRExpr
        decorators = self._norm_expr_list(node.decorator_list)

        return IRFunctionDef(
            name=node.name,
            params=self._normalize_arguments(node.args),
            body=self._normalize_body(node.body),
            return_type=ast.unparse(node.returns) if node.returns else None,
            is_async=False,
            is_generator=any(isinstance(n, (ast.Yield, ast.YieldFrom)) for n in ast.walk(node)),
            decorators=decorators,
            docstring=docstring,
            loc=self._make_loc(node),
            source_language=self.language,
        )

    def _normalize_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> IRFunctionDef:
        """Normalize async function definition."""
        # Reuse FunctionDef logic but set is_async=True
        result = self._normalize_FunctionDef(node)  # type: ignore
        result.is_async = True
        return result

    def _normalize_arguments(self, args: ast.arguments) -> list[IRParameter]:
        """Normalize function arguments."""
        params = []

        # Regular args
        defaults_offset = len(args.args) - len(args.defaults)
        for i, arg in enumerate(args.args):
            default_idx = i - defaults_offset
            default = None
            if default_idx >= 0:
                # [20251220_BUGFIX] Cast default value to IRExpr
                default = self._norm_expr(args.defaults[default_idx])

            params.append(
                IRParameter(
                    name=arg.arg,
                    type_annotation=(ast.unparse(arg.annotation) if arg.annotation else None),
                    default=default,
                    is_rest=False,
                    is_keyword_only=False,
                    loc=self._make_loc(arg),
                    source_language=self.language,
                )
            )

        # *args
        if args.vararg:
            params.append(
                IRParameter(
                    name=args.vararg.arg,
                    type_annotation=(ast.unparse(args.vararg.annotation) if args.vararg.annotation else None),
                    is_rest=True,
                    loc=self._make_loc(args.vararg),
                    source_language=self.language,
                )
            )

        # Keyword-only args
        kw_defaults_map = {i: d for i, d in enumerate(args.kw_defaults) if d is not None}
        for i, arg in enumerate(args.kwonlyargs):
            default = None
            if i in kw_defaults_map:
                # [20251220_BUGFIX] Cast default value to IRExpr
                default = self._norm_expr(kw_defaults_map[i])

            params.append(
                IRParameter(
                    name=arg.arg,
                    type_annotation=(ast.unparse(arg.annotation) if arg.annotation else None),
                    default=default,
                    is_keyword_only=True,
                    loc=self._make_loc(arg),
                    source_language=self.language,
                )
            )

        return params

    def _normalize_ClassDef(self, node: ast.ClassDef) -> IRClassDef:
        """Normalize class definition."""
        # Extract docstring
        docstring = None
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            docstring = node.body[0].value.value

        # [20251220_BUGFIX] Cast base classes and decorators to IRExpr
        bases = self._norm_expr_list(node.bases)
        decorators = self._norm_expr_list(node.decorator_list)

        return IRClassDef(
            name=node.name,
            bases=bases,
            body=self._normalize_body(node.body),
            decorators=decorators,
            docstring=docstring,
            loc=self._make_loc(node),
            source_language=self.language,
        )

    def _normalize_If(self, node: ast.If) -> IRIf:
        """Normalize if statement."""
        # [20251220_BUGFIX] Cast test to IRExpr
        return IRIf(
            test=self._norm_expr(node.test),
            body=self._normalize_body(node.body),
            orelse=self._normalize_body(node.orelse),
            loc=self._make_loc(node),
            source_language=self.language,
        )

    def _normalize_For(self, node: ast.For) -> IRFor:
        """Normalize for loop."""
        # [20251220_BUGFIX] Cast target and iter to IRExpr
        return IRFor(
            target=self._norm_expr(node.target),
            iter=self._norm_expr(node.iter),
            body=self._normalize_body(node.body),
            orelse=self._normalize_body(node.orelse),
            is_for_in=False,
            loc=self._make_loc(node),
            source_language=self.language,
        )

    def _normalize_While(self, node: ast.While) -> IRWhile:
        """Normalize while loop."""
        # [20251220_BUGFIX] Cast test to IRExpr
        return IRWhile(
            test=self._norm_expr(node.test),
            body=self._normalize_body(node.body),
            orelse=self._normalize_body(node.orelse),
            loc=self._make_loc(node),
            source_language=self.language,
        )

    def _normalize_Return(self, node: ast.Return) -> IRReturn:
        """Normalize return statement."""
        # [20251220_BUGFIX] Cast value to IRExpr | None
        return IRReturn(
            value=self._norm_expr(node.value) if node.value else None,
            loc=self._make_loc(node),
            source_language=self.language,
        )

    def _normalize_Assign(self, node: ast.Assign) -> IRAssign:
        """Normalize assignment statement."""
        # [20251220_BUGFIX] Cast targets and value to IRExpr
        return IRAssign(
            targets=self._norm_expr_list(node.targets),
            value=self._norm_expr(node.value),
            declaration_kind=None,  # Python doesn't have let/const/var
            loc=self._make_loc(node),
            source_language=self.language,
        )

    def _normalize_AnnAssign(self, node: ast.AnnAssign) -> IRAssign:
        """Normalize annotated assignment (x: int = 5)."""
        # [20251220_BUGFIX] Cast target and value to IRExpr; ensure targets is List[IRExpr]
        target = self._norm_expr(node.target)
        targets = [target] if target is not None else []
        return IRAssign(
            targets=targets,
            value=self._norm_expr(node.value) if node.value else None,
            declaration_kind=None,
            loc=self._make_loc(node),
            source_language=self.language,
        )

    def _normalize_AugAssign(self, node: ast.AugAssign) -> IRAugAssign:
        """Normalize augmented assignment (+=, -=, etc.)."""
        # [20251220_BUGFIX] Cast target and value to IRExpr
        return IRAugAssign(
            target=self._norm_expr(node.target),
            op=self._map_aug_assign_op(node.op),
            value=self._norm_expr(node.value),
            loc=self._make_loc(node),
            source_language=self.language,
        )

    def _normalize_Expr(self, node: ast.Expr) -> IRExprStmt:
        """Normalize expression statement."""
        # [20251220_BUGFIX] Cast value to IRExpr
        return IRExprStmt(
            value=self._norm_expr(node.value),
            loc=self._make_loc(node),
            source_language=self.language,
        )

    def _normalize_Pass(self, node: ast.Pass) -> IRPass:
        """Normalize pass statement."""
        return IRPass(
            loc=self._make_loc(node),
            source_language=self.language,
        )

    def _normalize_Break(self, node: ast.Break) -> IRBreak:
        """Normalize break statement."""
        return IRBreak(
            loc=self._make_loc(node),
            source_language=self.language,
        )

    def _normalize_Continue(self, node: ast.Continue) -> IRContinue:
        """Normalize continue statement."""
        return IRContinue(
            loc=self._make_loc(node),
            source_language=self.language,
        )

    # [20251218_FEATURE] Try/Except/Finally support
    def _normalize_Try(self, node: ast.Try) -> IRTry:
        """
        Normalize try/except/else/finally statement.

        [20251218_FEATURE] v3.0.1 - Full try/except support for Python IR.

        Python try statement structure:
            try:
                body
            except ExceptionType as name:
                handler_body
            else:
                orelse_body
            finally:
                finalbody
        """
        # Normalize try body
        body = self._normalize_body(node.body)

        # Normalize exception handlers
        handlers = []
        for handler in node.handlers:
            # handler.type is the exception type (can be None for bare except)
            exc_type = None
            if handler.type:
                exc_type = self.normalize_node(handler.type)

            # handler.name is the variable name (e.g., 'e' in 'except Exception as e')
            exc_name = handler.name

            # handler.body is the handler body
            handler_body = self._normalize_body(handler.body)

            handlers.append((exc_type, exc_name, handler_body))

        # Normalize else block (Python-specific)
        orelse = self._normalize_body(node.orelse) if node.orelse else []

        # Normalize finally block
        finalbody = self._normalize_body(node.finalbody) if node.finalbody else []

        return IRTry(
            body=body,
            handlers=handlers,
            orelse=orelse,
            finalbody=finalbody,
            loc=self._make_loc(node),
            source_language=self.language,
        )

    def _normalize_Raise(self, node: ast.Raise) -> IRRaise:
        """
        Normalize raise statement.

        [20251218_FEATURE] v3.0.1 - IRRaise support for Python.

        Python raise statement forms:
            raise                      # re-raise current exception
            raise Exception            # raise exception
            raise Exception from cause # raise with cause
        """
        # [20251220_BUGFIX] Cast exc and cause to IRExpr
        exc = self._norm_expr(node.exc) if node.exc else None
        cause = self._norm_expr(node.cause) if node.cause else None

        return IRRaise(
            exc=exc,
            cause=cause,
            loc=self._make_loc(node),
            source_language=self.language,
        )

    # Import statements - normalize to expression statements for now
    def _normalize_Import(self, node: ast.Import) -> IRExprStmt:
        """Normalize import statement (placeholder)."""
        # For now, represent as a call to __import__
        return IRExprStmt(
            value=IRCall(
                func=IRName(id="__import__", source_language=self.language),
                args=[IRConstant(value=alias.name, source_language=self.language) for alias in node.names],
                source_language=self.language,
            ),
            loc=self._make_loc(node),
            source_language=self.language,
        )

    def _normalize_ImportFrom(self, node: ast.ImportFrom) -> IRExprStmt:
        """Normalize from...import statement (placeholder)."""
        return IRExprStmt(
            value=IRCall(
                func=IRName(id="__import__", source_language=self.language),
                args=[IRConstant(value=node.module or "", source_language=self.language)],
                source_language=self.language,
            ),
            loc=self._make_loc(node),
            source_language=self.language,
        )

    # =========================================================================
    # Expressions
    # =========================================================================

    def _normalize_BinOp(self, node: ast.BinOp) -> IRBinaryOp:
        """Normalize binary operation."""
        # [20251220_BUGFIX] Cast operands to IRExpr
        return IRBinaryOp(
            left=self._norm_expr(node.left),
            op=self._map_binary_op(node.op),
            right=self._norm_expr(node.right),
            loc=self._make_loc(node),
            source_language=self.language,
        )

    def _normalize_Await(self, node: ast.Await) -> IRCall:
        """Normalize await expression as a special call."""
        # [20251220_BUGFIX] Cast value to IRExpr; ensure args is List[IRExpr]
        value = self._norm_expr(node.value)
        args = [value] if value is not None else []
        return IRCall(
            func=IRName(id="__await__", source_language=self.language),
            args=args,
            loc=self._make_loc(node),
            source_language=self.language,
        )

    def _normalize_UnaryOp(self, node: ast.UnaryOp) -> IRUnaryOp:
        """Normalize unary operation."""
        # [20251220_BUGFIX] Cast operand to IRExpr
        return IRUnaryOp(
            op=self._map_unary_op(node.op),
            operand=self._norm_expr(node.operand),
            loc=self._make_loc(node),
            source_language=self.language,
        )

    def _normalize_Compare(self, node: ast.Compare) -> IRCompare:
        """Normalize comparison operation."""
        # [20251220_BUGFIX] Cast left and comparators to IRExpr
        return IRCompare(
            left=self._norm_expr(node.left),
            ops=[self._map_cmp_op(op) for op in node.ops],
            comparators=self._norm_expr_list(node.comparators),
            loc=self._make_loc(node),
            source_language=self.language,
        )

    def _normalize_BoolOp(self, node: ast.BoolOp) -> IRBoolOp:
        """Normalize boolean operation (and/or)."""
        # [20251220_BUGFIX] Cast values to IRExpr
        return IRBoolOp(
            op=self._map_bool_op(node.op),
            values=self._norm_expr_list(node.values),
            loc=self._make_loc(node),
            source_language=self.language,
        )

    def _normalize_Call(self, node: ast.Call) -> IRCall:
        """Normalize function call."""
        # [20251220_BUGFIX] Cast func and args to IRExpr
        kwargs = {}
        for kw in node.keywords:
            if kw.arg:  # Named keyword
                kwargs[kw.arg] = self._norm_expr(kw.value)
            # **kwargs is complex, skip for now

        return IRCall(
            func=self._norm_expr(node.func),
            args=self._norm_expr_list(node.args),
            kwargs=kwargs,
            loc=self._make_loc(node),
            source_language=self.language,
        )

    def _normalize_Attribute(self, node: ast.Attribute) -> IRAttribute:
        """Normalize attribute access."""
        # [20251220_BUGFIX] Cast value to IRExpr
        return IRAttribute(
            value=self._norm_expr(node.value),
            attr=node.attr,
            loc=self._make_loc(node),
            source_language=self.language,
        )

    def _normalize_Subscript(self, node: ast.Subscript) -> IRSubscript:
        """Normalize subscript access."""
        # [20251220_BUGFIX] Cast value and slice to IRExpr
        return IRSubscript(
            value=self._norm_expr(node.value),
            slice=self._norm_expr(node.slice),
            loc=self._make_loc(node),
            source_language=self.language,
        )

    def _normalize_Name(self, node: ast.Name) -> IRName:
        """Normalize variable reference."""
        return IRName(
            id=node.id,
            loc=self._make_loc(node),
            source_language=self.language,
        )

    def _normalize_Constant(self, node: ast.Constant) -> IRConstant:
        """Normalize literal constant."""
        return IRConstant(
            value=node.value,
            raw=repr(node.value),
            loc=self._make_loc(node),
            source_language=self.language,
        )

    def _normalize_List(self, node: ast.List) -> IRList:
        """Normalize list literal."""
        # [20251220_BUGFIX] Cast elements to IRExpr
        return IRList(
            elements=self._norm_expr_list(node.elts),
            loc=self._make_loc(node),
            source_language=self.language,
        )

    def _normalize_Tuple(self, node: ast.Tuple) -> IRList:
        """Normalize tuple literal (treated as list in IR)."""
        # [20251220_BUGFIX] Cast elements to IRExpr
        result = IRList(
            elements=self._norm_expr_list(node.elts),
            loc=self._make_loc(node),
            source_language=self.language,
        )
        result._metadata["is_tuple"] = True
        return result

    def _normalize_Dict(self, node: ast.Dict) -> IRDict:
        """Normalize dict literal."""
        # [20251220_BUGFIX] Cast keys and values to IRExpr | None
        keys = [self._norm_expr(k) if k else None for k in node.keys]
        values = self._norm_expr_list(node.values)
        return IRDict(
            keys=keys,
            values=values,
            loc=self._make_loc(node),
            source_language=self.language,
        )

    def _normalize_IfExp(self, node: ast.IfExp) -> IRCall:
        """
        Normalize ternary expression (x if cond else y).

        Represented as a special call for now.
        """
        # [20251220_BUGFIX] Cast test, body, orelse to IRExpr; ensure args are non-None
        test = self._norm_expr(node.test) or IRConstant(value=False, source_language=self.language)
        body = self._norm_expr(node.body) or IRConstant(value=None, source_language=self.language)
        orelse = self._norm_expr(node.orelse) or IRConstant(value=None, source_language=self.language)
        return IRCall(
            func=IRName(id="__ternary__", source_language=self.language),
            args=[test, body, orelse],
            loc=self._make_loc(node),
            source_language=self.language,
        )

    def _normalize_Lambda(self, node: ast.Lambda) -> IRFunctionDef:
        """Normalize lambda expression."""
        # [20251220_BUGFIX] Cast body to IRExpr and wrap in IRReturn
        return IRFunctionDef(
            name="",  # Anonymous
            params=self._normalize_arguments(node.args),
            body=[
                IRReturn(
                    value=self._norm_expr(node.body),
                    source_language=self.language,
                )
            ],
            is_async=False,
            loc=self._make_loc(node),
            source_language=self.language,
        )

    # [20251214_FEATURE] v2.0.0 - List comprehension support for test generation
    def _normalize_ListComp(self, node: ast.ListComp) -> IRCall:
        """
        Normalize list comprehension to IR.

        [x * 2 for x in items if x > 0] becomes:
        __listcomp__(
            element=BinaryOp(Name('x'), MUL, Constant(2)),
            target=Name('x'),
            iter=Name('items'),
            conditions=[Compare(Name('x'), [GT], [Constant(0)])]
        )

        This representation preserves the semantic structure for:
        - Test generation (can analyze the element expression and conditions)
        - Type inference (can determine output type from element type)
        - Data flow analysis (can track which variables are used)

            - f-string expression parsing: f"value={expr}" as nested calls
            - JoinedStr normalization strategy for template strings
            - Walrus operator (named expressions): if (x := func()) > 0
            - Match/case statements (Python 3.10+)
            - Type aliases and type parameter syntax (3.12+)

            - Async list/dict/set comprehensions
            - Async generator expressions
            - Async for loops in comprehensions

            - Decorator argument normalization
            - Stacked decorator tracking
            - Class and method decorator analysis
        """
        # Get the first generator (most common case)
        # For nested comprehensions, we'd need to handle multiple generators
        if not node.generators:
            # Shouldn't happen in valid Python, but handle gracefully
            # [20251220_BUGFIX] Cast elt to IRExpr
            elt = self._norm_expr(node.elt) or IRConstant(value=None, source_language=self.language)
            return IRCall(
                func=IRName(id="__listcomp__", source_language=self.language),
                args=[elt],
                loc=self._make_loc(node),
                source_language=self.language,
            )

        gen = node.generators[0]

        # Normalize the comprehension components
        # [20251220_BUGFIX] Cast all expressions to IRExpr
        element_expr = self._norm_expr(node.elt) or IRConstant(value=None, source_language=self.language)
        target_expr = self._norm_expr(gen.target) or IRName(id="_", source_language=self.language)
        iter_expr = self._norm_expr(gen.iter) or IRConstant(value=None, source_language=self.language)

        # Normalize filter conditions (if any)
        # [20251220_BUGFIX] Cast conditions to IRExpr list
        conditions = [
            c or IRConstant(value=True, source_language=self.language)
            for c in [self._norm_expr(cond) for cond in gen.ifs]
        ]

        # For nested generators, we can chain them
        # But for v2.0.0, focus on single-level comprehensions
        call = IRCall(
            func=IRName(id="__listcomp__", source_language=self.language),
            args=[element_expr, target_expr, iter_expr],
            kwargs=({"conditions": IRList(elements=conditions, source_language=self.language)} if conditions else {}),
            loc=self._make_loc(node),
            source_language=self.language,
        )

        # Mark metadata for nested generators
        if len(node.generators) > 1:
            call._metadata["nested_generators"] = len(node.generators)

        return call

    def _normalize_SetComp(self, node: ast.SetComp) -> IRCall:
        """
        [20251214_FEATURE] v2.0.0 - Normalize set comprehension.

        {x for x in items} -> __setcomp__(element, target, iter)
        """
        if not node.generators:
            # [20251220_BUGFIX] Cast elt to IRExpr
            elt = self._norm_expr(node.elt) or IRConstant(value=None, source_language=self.language)
            return IRCall(
                func=IRName(id="__setcomp__", source_language=self.language),
                args=[elt],
                loc=self._make_loc(node),
                source_language=self.language,
            )

        gen = node.generators[0]
        # [20251220_BUGFIX] Cast expressions to IRExpr
        element_expr = self._norm_expr(node.elt) or IRConstant(value=None, source_language=self.language)
        target_expr = self._norm_expr(gen.target) or IRName(id="_", source_language=self.language)
        iter_expr = self._norm_expr(gen.iter) or IRConstant(value=None, source_language=self.language)
        conditions = [
            c or IRConstant(value=True, source_language=self.language)
            for c in [self._norm_expr(cond) for cond in gen.ifs]
        ]

        return IRCall(
            func=IRName(id="__setcomp__", source_language=self.language),
            args=[element_expr, target_expr, iter_expr],
            kwargs=({"conditions": IRList(elements=conditions, source_language=self.language)} if conditions else {}),
            loc=self._make_loc(node),
            source_language=self.language,
        )

    def _normalize_DictComp(self, node: ast.DictComp) -> IRCall:
        """
        [20251214_FEATURE] v2.0.0 - Normalize dict comprehension.

        {k: v for k, v in items} -> __dictcomp__(key, value, target, iter)
        """
        if not node.generators:
            # [20251220_BUGFIX] Cast key and value to IRExpr
            key = self._norm_expr(node.key) or IRConstant(value=None, source_language=self.language)
            value = self._norm_expr(node.value) or IRConstant(value=None, source_language=self.language)
            return IRCall(
                func=IRName(id="__dictcomp__", source_language=self.language),
                args=[key, value],
                loc=self._make_loc(node),
                source_language=self.language,
            )

        gen = node.generators[0]
        # [20251220_BUGFIX] Cast all expressions to IRExpr
        key_expr = self._norm_expr(node.key) or IRConstant(value=None, source_language=self.language)
        value_expr = self._norm_expr(node.value) or IRConstant(value=None, source_language=self.language)
        target_expr = self._norm_expr(gen.target) or IRName(id="_", source_language=self.language)
        iter_expr = self._norm_expr(gen.iter) or IRConstant(value=None, source_language=self.language)
        conditions = [
            c or IRConstant(value=True, source_language=self.language)
            for c in [self._norm_expr(cond) for cond in gen.ifs]
        ]

        return IRCall(
            func=IRName(id="__dictcomp__", source_language=self.language),
            args=[key_expr, value_expr, target_expr, iter_expr],
            kwargs=({"conditions": IRList(elements=conditions, source_language=self.language)} if conditions else {}),
            loc=self._make_loc(node),
            source_language=self.language,
        )

    def _normalize_GeneratorExp(self, node: ast.GeneratorExp) -> IRCall:
        """
        [20251214_FEATURE] v2.0.0 - Normalize generator expression.

        (x for x in items) -> __genexp__(element, target, iter)
        """
        if not node.generators:
            # [20251220_BUGFIX] Cast elt to IRExpr
            elt = self._norm_expr(node.elt) or IRConstant(value=None, source_language=self.language)
            return IRCall(
                func=IRName(id="__genexp__", source_language=self.language),
                args=[elt],
                loc=self._make_loc(node),
                source_language=self.language,
            )

        gen = node.generators[0]
        # [20251220_BUGFIX] Cast expressions to IRExpr
        element_expr = self._norm_expr(node.elt) or IRConstant(value=None, source_language=self.language)
        target_expr = self._norm_expr(gen.target) or IRName(id="_", source_language=self.language)
        iter_expr = self._norm_expr(gen.iter) or IRConstant(value=None, source_language=self.language)
        conditions = [
            c or IRConstant(value=True, source_language=self.language)
            for c in [self._norm_expr(cond) for cond in gen.ifs]
        ]

        return IRCall(
            func=IRName(id="__genexp__", source_language=self.language),
            args=[element_expr, target_expr, iter_expr],
            kwargs=({"conditions": IRList(elements=conditions, source_language=self.language)} if conditions else {}),
            loc=self._make_loc(node),
            source_language=self.language,
        )

    # Slice is used in subscripts
    def _normalize_Slice(self, node: ast.Slice) -> IRCall:
        """Normalize slice (a:b:c)."""
        # [20251220_BUGFIX] Cast slice bounds to IRExpr with defaults
        lower = self._norm_expr(node.lower) or IRConstant(value=None, source_language=self.language)
        upper = self._norm_expr(node.upper) or IRConstant(value=None, source_language=self.language)
        step = self._norm_expr(node.step) or IRConstant(value=None, source_language=self.language)
        return IRCall(
            func=IRName(id="slice", source_language=self.language),
            args=[lower, upper, step],
            loc=self._make_loc(node),
            source_language=self.language,
        )

    # =========================================================================
    # Operator Mappings
    # =========================================================================

    def _map_binary_op(self, op: ast.operator) -> BinaryOperator:
        """Map Python ast operator to IR BinaryOperator."""
        mapping = {
            ast.Add: BinaryOperator.ADD,
            ast.Sub: BinaryOperator.SUB,
            ast.Mult: BinaryOperator.MUL,
            ast.Div: BinaryOperator.DIV,
            ast.FloorDiv: BinaryOperator.FLOOR_DIV,
            ast.Mod: BinaryOperator.MOD,
            ast.Pow: BinaryOperator.POW,
            ast.BitAnd: BinaryOperator.BIT_AND,
            ast.BitOr: BinaryOperator.BIT_OR,
            ast.BitXor: BinaryOperator.BIT_XOR,
            ast.LShift: BinaryOperator.LSHIFT,
            ast.RShift: BinaryOperator.RSHIFT,
            ast.MatMult: BinaryOperator.MATMUL,
        }
        return mapping.get(type(op), BinaryOperator.ADD)

    def _map_unary_op(self, op: ast.unaryop) -> UnaryOperator:
        """Map Python ast unary operator to IR UnaryOperator."""
        mapping = {
            ast.UAdd: UnaryOperator.POS,
            ast.USub: UnaryOperator.NEG,
            ast.Not: UnaryOperator.NOT,
            ast.Invert: UnaryOperator.INVERT,
        }
        return mapping.get(type(op), UnaryOperator.NEG)

    def _map_cmp_op(self, op: ast.cmpop) -> CompareOperator:
        """Map Python ast comparison operator to IR CompareOperator."""
        mapping = {
            ast.Eq: CompareOperator.EQ,
            ast.NotEq: CompareOperator.NE,
            ast.Lt: CompareOperator.LT,
            ast.LtE: CompareOperator.LE,
            ast.Gt: CompareOperator.GT,
            ast.GtE: CompareOperator.GE,
            ast.Is: CompareOperator.IS,
            ast.IsNot: CompareOperator.IS_NOT,
            ast.In: CompareOperator.IN,
            ast.NotIn: CompareOperator.NOT_IN,
        }
        return mapping.get(type(op), CompareOperator.EQ)

    def _map_bool_op(self, op: ast.boolop) -> BoolOperator:
        """Map Python ast boolean operator to IR BoolOperator."""
        mapping = {
            ast.And: BoolOperator.AND,
            ast.Or: BoolOperator.OR,
        }
        return mapping.get(type(op), BoolOperator.AND)

    def _map_aug_assign_op(self, op: ast.operator) -> AugAssignOperator:
        """Map Python ast operator to IR AugAssignOperator."""
        mapping = {
            ast.Add: AugAssignOperator.ADD,
            ast.Sub: AugAssignOperator.SUB,
            ast.Mult: AugAssignOperator.MUL,
            ast.Div: AugAssignOperator.DIV,
            ast.FloorDiv: AugAssignOperator.FLOOR_DIV,
            ast.Mod: AugAssignOperator.MOD,
            ast.Pow: AugAssignOperator.POW,
            ast.BitAnd: AugAssignOperator.BIT_AND,
            ast.BitOr: AugAssignOperator.BIT_OR,
            ast.BitXor: AugAssignOperator.BIT_XOR,
            ast.LShift: AugAssignOperator.LSHIFT,
            ast.RShift: AugAssignOperator.RSHIFT,
            ast.MatMult: AugAssignOperator.MATMUL,
        }
        return mapping.get(type(op), AugAssignOperator.ADD)
