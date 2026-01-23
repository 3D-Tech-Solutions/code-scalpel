"""
Unified IR Node Definitions.

These dataclasses represent the STRUCTURE of programs in a language-agnostic way.
All nodes track their source_language for semantic dispatch.

Design Principles:
    1. Minimal - Only include nodes needed for analysis
    2. Semantic - Represent meaning, not syntax (no commas, parentheses, etc.)
    3. Typed - All fields have type annotations
    4. Immutable-ish - Use dataclasses with default_factory for lists

Node Categories:
    - Statements: IRModule, IRFunctionDef, IRIf, IRFor, IRWhile, IRAssign, etc.
    - Expressions: IRBinaryOp, IRUnaryOp, IRCall, IRName, IRConstant, etc.
    - Special: IRParameter, SourceLocation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Union

from .operators import (
    AugAssignOperator,
    BinaryOperator,
    BoolOperator,
    CompareOperator,
    UnaryOperator,
)


@dataclass
class SourceLocation:
    """
    Source code location for error reporting and debugging.

    Attributes:
        line: 1-indexed line number
        column: 0-indexed column offset
        end_line: End line (optional, for multi-line nodes)
        end_column: End column (optional)
        filename: Source file path (optional)
    """

    line: int
    column: int
    end_line: int | None = None
    end_column: int | None = None
    filename: str | None = None

    def __str__(self) -> str:
        if self.filename:
            return f"{self.filename}:{self.line}:{self.column}"
        return f"line {self.line}, col {self.column}"


# =============================================================================
# Base Node
# =============================================================================


@dataclass
class IRNode:
    """
    Base class for all Unified IR nodes.

    Every node tracks:
        - loc: Source location for error messages
        - source_language: Original language for semantic dispatch
        - _metadata: Extensible dict for analysis passes

    The source_language field is CRITICAL for correct semantics:
        - Python "5" + 3 -> TypeError
        - JavaScript "5" + 3 -> "53"

    Analysis engines use source_language to select the right LanguageSemantics.

        - parent_node tracking for traversal
        - children() method for generic iteration
        - clone_with_updates() for immutable-style updates
        - hash() and equality for caching/deduplication
        - accept(visitor) for visitor pattern

        - value_constraints for range/type constraints
        - possible_types for union types
        - is_null_coalescing for nullish tracking
        - error_handling_context for try/catch tracking
    """

    loc: SourceLocation | None = None
    source_language: str = "unknown"
    _metadata: dict[str, Any] = field(default_factory=dict)

    def with_metadata(self, key: str, value: Any) -> IRNode:
        """Add metadata and return self for chaining."""
        self._metadata[key] = value
        return self


# =============================================================================
# Statement Nodes
# =============================================================================


@dataclass
class IRModule(IRNode):
    """
    Root node representing a source file/module.

    Attributes:
        body: List of top-level statements
        docstring: Module docstring if present
    """

    body: list[IRNode] = field(default_factory=list)
    docstring: str | None = None


@dataclass
class IRFunctionDef(IRNode):
    """
    Function definition.

    Covers:
        - Python: def foo(), async def foo()
        - JavaScript: function foo(), async function foo(), arrow functions

    Attributes:
        name: Function name (empty string for anonymous functions)
        params: List of parameters
        body: List of statements in function body
        return_type: Type annotation string if present (Python type hints, TS types)
        is_async: Whether function is async
        is_generator: Whether function is a generator (yield)
        decorators: List of decorator expressions (Python-specific)
    """

    name: str = ""
    params: list[IRParameter] = field(default_factory=list)
    body: list[IRNode] = field(default_factory=list)
    return_type: str | None = None
    is_async: bool = False
    is_generator: bool = False
    decorators: list[IRExpr] = field(default_factory=list)
    docstring: str | None = None


@dataclass
class IRClassDef(IRNode):
    """
    Class definition.

    Covers:
        - Python: class Foo(Base)
        - JavaScript: class Foo extends Base

    Attributes:
        name: Class name
        bases: Base classes/superclasses
        body: Class body (methods, properties)
        decorators: Class decorators (Python-specific)
    """

    name: str = ""
    bases: list[IRExpr] = field(default_factory=list)
    body: list[IRNode] = field(default_factory=list)
    decorators: list[IRExpr] = field(default_factory=list)
    docstring: str | None = None


@dataclass
class IRIf(IRNode):
    """
    If statement with optional elif/else chain.

    The orelse field contains:
        - Empty list: no else
        - Single IRIf: elif chain
        - Other statements: else block

    Attributes:
        test: Condition expression
        body: Statements in if-true branch
        orelse: Statements in else branch (may be another IRIf for elif)
    """

    # [20251220_BUGFIX] Fixed optional field types - test can be None in some contexts
    test: IRExpr | None = None
    body: list[IRNode] = field(default_factory=list)
    orelse: list[IRNode] = field(default_factory=list)


@dataclass
class IRFor(IRNode):
    """
    For loop (iteration over collection).

    Covers:
        - Python: for x in iterable
        - JavaScript: for (let x of iterable), for (let x in obj)

    Attributes:
        target: Loop variable (IRName or destructuring pattern)
        iter: Iterable expression
        body: Loop body statements
        orelse: Python's for-else clause (empty for JS)
        is_for_in: True for JS for-in (iterate keys), False for for-of (iterate values)
    """

    # [20251220_BUGFIX] Fixed optional field types - target and iter can be None in some contexts
    target: IRExpr | None = None
    iter: IRExpr | None = None
    body: list[IRNode] = field(default_factory=list)
    orelse: list[IRNode] = field(default_factory=list)
    is_for_in: bool = False  # JS for-in vs for-of


@dataclass
class IRWhile(IRNode):
    """
    While loop.

    Attributes:
        test: Condition expression
        body: Loop body statements
        orelse: Python's while-else clause (empty for JS)
    """

    # [20251220_BUGFIX] Fixed optional field type - test can be None in some contexts
    test: IRExpr | None = None
    body: list[IRNode] = field(default_factory=list)
    orelse: list[IRNode] = field(default_factory=list)


@dataclass
class IRReturn(IRNode):
    """
    Return statement.

    Attributes:
        value: Return value expression (None for bare return)
    """

    # [20251220_BUGFIX] Fixed optional field type - value can be None for bare return
    value: IRExpr | None = None


@dataclass
class IRAssign(IRNode):
    """
    Assignment statement.

    Covers:
        - Python: x = 1, x = y = 1
        - JavaScript: let x = 1, const x = 1, x = 1

    Attributes:
        targets: Assignment targets (multiple for chained assignment)
        value: Value being assigned
        declaration_kind: "let", "const", "var" for JS; None for Python
    """

    targets: list[IRExpr] = field(default_factory=list)
    # [20251220_BUGFIX] Fixed optional field type - value can be None in some contexts
    value: IRExpr | None = None
    declaration_kind: str | None = None  # "let", "const", "var" for JS


@dataclass
class IRAugAssign(IRNode):
    """
    Augmented assignment (+=, -=, etc.).

    Attributes:
        target: Assignment target
        op: Augmented assignment operator
        value: Value to combine with target
    """

    # [20251220_BUGFIX] Fixed optional field types - target, op, and value can be None in some contexts
    target: IRExpr | None = None
    op: AugAssignOperator | None = None
    value: IRExpr | None = None


@dataclass
class IRExprStmt(IRNode):
    """
    Expression statement (expression used as statement).

    Example: function call as statement: `print("hello")`

    Attributes:
        value: The expression
    """

    # [20251220_BUGFIX] Fixed optional field type - value can be None in some contexts
    value: IRExpr | None = None


@dataclass
class IRPass(IRNode):
    """
    Pass/no-op statement.

    Python: pass
    JavaScript: ; (empty statement)
    """

    pass


@dataclass
class IRBreak(IRNode):
    """Break statement - exit loop."""

    pass


@dataclass
class IRContinue(IRNode):
    """Continue statement - skip to next iteration."""

    pass


# [20251215_FEATURE] v2.0.0 - Import/Export support for polyglot extraction
@dataclass
class IRImport(IRNode):
    """
    Import statement (ES6 modules, Python imports, Java imports).

    Examples:
        Python: import foo, from foo import bar
        JavaScript: import { bar } from 'foo', import foo from 'foo'
        Java: import com.example.Foo

    Attributes:
        module: Module path/name being imported
        names: List of imported names (empty for default import)
        alias: Alias for the import (as name)
        is_default: True for default import (JS: import x from 'y')
        is_star: True for star import (from x import *)
    """

    module: str = ""
    names: list[str] = field(default_factory=list)
    alias: str | None = None
    is_default: bool = False
    is_star: bool = False


@dataclass
class IRExport(IRNode):
    """
    Export statement (ES6 modules).

    Examples:
        export default function() {}
        export { foo, bar }
        export const x = 1

    Attributes:
        names: List of exported names
        declaration: Exported declaration (function, class, variable)
        is_default: True for default export
        source: Re-export source module (export { x } from 'y')
    """

    names: list[str] = field(default_factory=list)
    declaration: IRNode | None = None
    is_default: bool = False
    source: str | None = None


@dataclass
class IRSwitch(IRNode):
    """
    Switch statement.

    Attributes:
        discriminant: Expression being switched on
        cases: List of (test, body) tuples. test=None for default case.
    """

    # [20251220_BUGFIX] Fixed optional field type - discriminant can be None in some contexts
    discriminant: IRExpr | None = None
    cases: list[tuple] = field(default_factory=list)  # [(test, [body]), ...]


@dataclass
class IRTry(IRNode):
    """
    Try/catch/finally statement.

    Attributes:
        body: Try block statements
        handlers: List of (exception_type, name, body) tuples
        orelse: Else block (Python only)
        finalbody: Finally block statements
    """

    body: list[IRNode] = field(default_factory=list)
    handlers: list[tuple] = field(default_factory=list)  # [(type, name, body), ...]
    orelse: list[IRNode] = field(default_factory=list)
    finalbody: list[IRNode] = field(default_factory=list)


@dataclass
class IRRaise(IRNode):
    """
    Raise/throw statement.

    Attributes:
        exc: Exception expression to raise
        cause: Exception cause (Python 'from' clause)
    """

    exc: IRExpr | None = None
    cause: IRExpr | None = None


# =============================================================================
# Expression Nodes
# =============================================================================


@dataclass
class IRExpr(IRNode):
    """
    Base class for expression nodes.

    Expressions produce values and can be nested.
    """

    pass


@dataclass
class IRBinaryOp(IRExpr):
    """
    Binary operation (a + b, a * b, etc.).

    IMPORTANT: The operator is structural, not semantic.
    BinaryOperator.ADD means "the add operation" but its BEHAVIOR
    depends on source_language (Python vs JS string coercion).

    Attributes:
        left: Left operand
        op: Binary operator
        right: Right operand

        - Store precedence level for pretty-printing
        - Store associativity (left/right) for nested operations
        - Enable parenthesis elision in code generation

        - Flag operations that may overflow in target language
        - Track integer division vs float division
        - Mark potential NaN or Infinity results (JS)
    """

    # [20251220_BUGFIX] Fixed optional field types - left, op, and right can be None in some contexts
    left: IRExpr | None = None
    op: BinaryOperator | None = None
    right: IRExpr | None = None


@dataclass
class IRUnaryOp(IRExpr):
    """
    Unary operation (-x, not x, ~x, etc.).

    Attributes:
        op: Unary operator
        operand: The operand expression
    """

    # [20251220_BUGFIX] Fixed optional field types - op and operand can be None in some contexts
    op: UnaryOperator | None = None
    operand: IRExpr | None = None


@dataclass
class IRCompare(IRExpr):
    """
    Comparison operation.

    Supports chained comparisons (Python: a < b < c).
    JavaScript comparisons are single: ops=[EQ], comparators=[right].

    Attributes:
        left: Left-most value
        ops: List of comparison operators
        comparators: List of values to compare (parallel to ops)

    Example (Python a < b < c):
        left=a, ops=[LT, LT], comparators=[b, c]
        Means: a < b AND b < c
    """

    # [20251220_BUGFIX] Fixed optional field type - left can be None in some contexts
    left: IRExpr | None = None
    ops: list[CompareOperator] = field(default_factory=list)
    comparators: list[IRExpr] = field(default_factory=list)


@dataclass
class IRBoolOp(IRExpr):
    """
    Boolean/logical operation (and, or).

    Short-circuit evaluation semantics depend on source_language.

    Attributes:
        op: Boolean operator (AND or OR)
        values: List of operands (at least 2)
    """

    # [20251220_BUGFIX] Fixed optional field type - op can be None in some contexts
    op: BoolOperator | None = None
    values: list[IRExpr] = field(default_factory=list)


# [20251215_FEATURE] v2.0.0 - Ternary/conditional expression for polyglot support
@dataclass
class IRTernary(IRExpr):
    """
    Ternary/conditional expression.

    Python: x if condition else y
    JavaScript/Java: condition ? x : y

    Attributes:
        test: Condition expression
        body: Value if true
        orelse: Value if false
    """

    # [20251220_BUGFIX] Fixed optional field types - test, body, and orelse can be None in some contexts
    test: IRExpr | None = None
    body: IRExpr | None = None
    orelse: IRExpr | None = None


@dataclass
class IRCall(IRExpr):
    """
    Function/method call.

        - func: The function being called
        - args: Positional arguments
        - keywords: Keyword arguments (name, value) tuples
        - Add spread_args flag for ...args in JS
        - Add await_result flag for awaited calls
        - Add is_super flag for super() calls
    """

    """
    Function/method call.

    Attributes:
        func: The callable expression (IRName, IRAttribute, etc.)
        args: Positional arguments
        kwargs: Keyword arguments (name -> value)
    """

    # [20251220_BUGFIX] Fixed optional field type - func can be None in some contexts
    func: IRExpr | None = None
    args: list[IRExpr] = field(default_factory=list)
    kwargs: dict[str, IRExpr] = field(default_factory=dict)


@dataclass
class IRAttribute(IRExpr):
    """
    Attribute access (obj.attr).

    Attributes:
        value: The object expression
        attr: The attribute name
    """

    # [20251220_BUGFIX] Fixed optional field type - value can be None in some contexts
    value: IRExpr | None = None
    attr: str = ""


@dataclass
class IRSubscript(IRExpr):
    """
    Subscript/index access (obj[key]).

    Attributes:
        value: The object expression
        slice: The index/key expression
    """

    # [20251220_BUGFIX] Fixed optional field types - value and slice can be None in some contexts
    value: IRExpr | None = None
    slice: IRExpr | None = None


@dataclass
class IRName(IRExpr):
    """
    Variable/identifier reference.

    Attributes:
        id: The variable name
    """

    id: str = ""


@dataclass
class IRConstant(IRExpr):
    """
    Literal constant value.

    Covers:
        - Numbers: 42, 3.14
        - Strings: "hello", 'world'
        - Booleans: True/False, true/false
        - None/null/undefined

    Attributes:
        value: The Python-native value
        raw: Original source representation (for preserving "undefined" vs "null")
    """

    value: Any = None
    raw: str | None = None  # Preserves "undefined" vs "null" distinction


@dataclass
class IRList(IRExpr):
    """
    List/Array literal.

    Attributes:
        elements: List of element expressions
    """

    elements: list[IRExpr] = field(default_factory=list)


@dataclass
class IRDict(IRExpr):
    """
    Dictionary/Object literal.

    Attributes:
        keys: List of key expressions (None for spread: {...x})
        values: List of value expressions
    """

    keys: list[IRExpr | None] = field(default_factory=list)
    values: list[IRExpr] = field(default_factory=list)


@dataclass
class IRParameter(IRNode):
    """
    Function parameter.

    Attributes:
        name: Parameter name
        type_annotation: Type annotation string if present
        default: Default value expression if present
        is_rest: True for rest parameters (*args, ...args)
        is_keyword_only: True for Python keyword-only params (after *)
    """

    name: str = ""
    type_annotation: str | None = None
    default: IRExpr | None = None
    is_rest: bool = False
    is_keyword_only: bool = False


# =============================================================================
# Type Aliases for Convenience
# =============================================================================

# Any statement node
IRStmt = Union[
    IRModule,
    IRFunctionDef,
    IRClassDef,
    IRIf,
    IRFor,
    IRWhile,
    IRReturn,
    IRAssign,
    IRAugAssign,
    IRExprStmt,
    IRPass,
    IRBreak,
    IRContinue,
    # [20251215_FEATURE] v2.0.0 - New statement types
    IRImport,
    IRExport,
    IRSwitch,
    IRTry,
    IRRaise,
]

# Any node
AnyIRNode = Union[IRStmt, IRExpr, IRParameter]
