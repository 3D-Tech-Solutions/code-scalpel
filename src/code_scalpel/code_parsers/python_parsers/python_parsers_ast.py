#!/usr/bin/env python3
"""
Python AST Parser - Core Abstract Syntax Tree Analysis.
========================================================

This module provides comprehensive Python AST analysis capabilities including
symbol extraction, scope analysis, control flow graphs, and data flow analysis.

This is the HIGHEST PRIORITY module as it forms the foundation for all other
Python analysis tools.

Implementation Status: COMPLETED
Priority: P1 - CRITICAL

==============================================================================
FIXES LOG - Type Safety and Linting Issues Resolution
==============================================================================
Date: December 21, 2025
Category: TYPE_SAFETY_IMPROVEMENTS
Status: ✓ ALL 31 LINTING ERRORS FIXED (0 errors remaining)

Summary:
This session resolved all 31 type-related linting errors in python_parsers_ast.py
by implementing defensive programming patterns, proper type narrowing with isinstance()
checks, and explicit parameter handling instead of unpacking.

Fixes Applied (31 total):

1. TYPE_NARROWING_UNION_TYPES (2 fixes):
   - Line 582: Added isinstance(n, ast.expr) check in collect_union_members()
   - Line 658: Added isinstance(node, ast.expr) check in _parse_slice_elements()
   Purpose: Ensure only expr nodes passed to TypeAnnotation.from_node()

2. OPTIONAL_VALUE_HANDLING (1 fix):
   - Line 1661: Added isinstance(kw_default, ast.expr) guard for ast.unparse()
   Purpose: Handle kw_defaults[i] that can be None in keyword-only parameters

3. CONTROL_FLOW_NONE_SAFETY (8 fixes - CFGBuilder methods):
   - Line 2753: _visit_if() - Guard access to current_block.statements
   - Line 2744: _visit_stmt() - Guard nested definition and simple statement handling
   - Line 2967: _visit_with() - Guard context manager statement appending
   - Line 2987: _visit_match() - Guard match_block statement appending
   - Line 3006: _visit_return() - Guard return statement appending
   - Line 3021: _visit_raise() - Guard raise statement appending
   - Line 3035: _visit_break() - Guard break statement appending
   - Line 3045: _visit_continue() - Guard continue statement appending
   Purpose: Prevent "statements is not a known attribute of None" errors when
            current_block becomes None after terminal statements

4. EXPLICIT_PARAMETER_ASSIGNMENT (2 fixes):
   - Line 1763-1780: visit_FunctionDef() - Replaced **props unpacking with explicit
                      assignment for staticmethod, classmethod, property, abstractmethod
   - Line 1797-1810: visit_AsyncFunctionDef() - Same pattern as FunctionDef
   Purpose: Avoid type mismatch errors when unpacking dict with Union type values

5. UNION_TYPE_ATTRIBUTE_ACCESS (1 fix):
   - Line 3219-3221: _collect_assignments() - Added isinstance(stmt.target, ast.Name)
                      check before accessing .id attribute in walrus operator handling
   Purpose: Prevent "Cannot access attribute id for class Attribute/Subscript" errors

Implementation Notes:
- All fixes follow Python best practices for defensive programming
- Type guards use isinstance() for runtime type narrowing
- Optional values checked before use with None guards
- Explicit parameter assignment prevents Union type unpacking errors
- CFGBuilder methods now safely handle None current_block state
- Pattern-based fixes can be applied to any similar code structures

Test Validation:
- Linting: 31 errors → 0 errors (verified with get_errors tool)
- Type checking: All type narrowing paths properly guarded
- Runtime safety: Added defensive checks prevent AttributeError exceptions
- Code integrity: No functional changes, only type safety improvements

Related Files Fixed in Same Session:
- python_parsers/__init__.py (0 errors - fixed import resolution)
- python_parsers_pydocstyle.py (status markers updated)
- python_parsers_prospector.py (status markers updated)

Completed Features:
- [✓] P1-AST-001: Comprehensive node visitor with parent tracking
- [✓] P1-AST-002: Symbol table generation
- [✓] P1-AST-003: Scope analysis (LEGB rule)
- [✓] P1-AST-004: Name binding and reference resolution
- [✓] P2-AST-005: Call graph generation
- [✓] P2-AST-006: Control flow graph generation
- [✓] P2-AST-007: Data flow analysis
- [✓] P2-AST-008: Type annotation extraction

==============================================================================
COMPLETED [P1-AST-001]: PythonASTParser with comprehensive node visitor
==============================================================================
Priority: CRITICAL
Status: ✓ COMPLETED

Implemented Features:
    - [✓] Create base visitor using ast.NodeVisitor (ParentTrackingVisitor)
    - [✓] Handle all Python 3.12 node types gracefully
    - [✓] Track source locations (line, column, end_line, end_column)
    - [✓] Build parent-child relationships
    - [✓] Handle syntax errors with partial AST recovery
    - [✓] Support both file and string input
    - [—] Preserve comments via tokenize module (out of scope - AST discards comments)

Implementation Notes:
    ```python
    class ComprehensiveNodeVisitor(ast.NodeVisitor):
        def __init__(self):
            self.parent_stack: list[ast.AST] = []
            self.node_parents: dict[ast.AST, ast.AST | None] = {}

        def visit(self, node: ast.AST) -> Any:
            self.node_parents[node] = self.parent_stack[-1] if self.parent_stack else None
            self.parent_stack.append(node)
            result = super().visit(node)
            self.parent_stack.pop()
            return result
    ```

Test Cases:
    - Parse valid Python file and verify AST structure
    - Parse file with syntax error and get partial results
    - Verify line/column numbers match source
    - Parse all Python 3.12 syntax features

==============================================================================
COMPLETED [P1-AST-002]: Symbol table generation
==============================================================================
Priority: CRITICAL
Status: ✓ COMPLETED

Implemented Features:
    - [✓] Extract function definitions (def, async def, lambda)
    - [✓] Extract class definitions (class, dataclass, Protocol)
    - [✓] Extract variable assignments (=, :=, augmented)
    - [✓] Extract type annotations (variable and function)
    - [✓] Extract import statements (import, from...import, *)
    - [✓] Build qualified names for nested symbols
    - [✓] Track decorators on functions/classes
    - [✓] Track base classes and metaclasses

Data Structures:
    ```python
    @dataclass
    class PythonSymbol:
        name: str
        qualified_name: str  # e.g., "module.Class.method"
        kind: SymbolKind  # FUNCTION, CLASS, VARIABLE, IMPORT, PARAMETER
        line: int
        column: int
        end_line: int
        end_column: int
        parent: PythonSymbol | None
        docstring: str | None
        decorators: list[str]
        type_annotation: str | None
    ```

Test Cases:
    - Extract symbols from module with nested classes/functions
    - Verify qualified names are correct
    - Handle lambda functions and comprehensions
    - Extract decorators and annotations

==============================================================================
COMPLETED [P1-AST-003]: Scope analysis (LEGB rule)
==============================================================================
Priority: CRITICAL
Status: ✓ COMPLETED

Implemented Features:
    - [✓] Identify Local scope boundaries
    - [✓] Detect Enclosing (nonlocal) scope references
    - [✓] Track Global scope declarations
    - [✓] Detect Builtin shadowing
    - [✓] Identify free variables (closure variables)
    - [✓] Track cell variables (variables referenced in nested functions)
    - [✓] Handle 'global' and 'nonlocal' keywords
    - [✓] Detect class scope quirks (no LEGB for class body)

Data Structures:
    ```python
    class ScopeType(Enum):
        MODULE = "module"
        CLASS = "class"
        FUNCTION = "function"
        COMPREHENSION = "comprehension"
        LAMBDA = "lambda"

    @dataclass
    class PythonScope:
        type: ScopeType
        name: str
        parent: PythonScope | None
        children: list[PythonScope]
        local_names: set[str]
        global_names: set[str]  # Names declared 'global'
        nonlocal_names: set[str]  # Names declared 'nonlocal'
        free_variables: set[str]  # Referenced from enclosing scope
        cell_variables: set[str]  # Referenced by nested scopes
    ```

Test Cases:
    - Closures with free/cell variable tracking
    - Global/nonlocal keyword handling
    - Class scope not part of LEGB for nested functions
    - Builtin shadowing detection

==============================================================================
COMPLETED [P1-AST-004]: Name binding and reference resolution
==============================================================================
Priority: CRITICAL
Status: ✓ COMPLETED

Implemented Features:
    - [✓] Bind each Name node to its definition
    - [✓] Distinguish read vs write access (Load, Store, Del contexts)
    - [✓] Identify undefined name references
    - [✓] Handle import aliases correctly
    - [~] Resolve * imports using __all__ when available (partial - requires runtime)
    - [✓] Track augmented assignments (x += 1 is both read and write)
    - [✓] Handle walrus operator (:=) scope rules
    - [✓] Handle comprehension scoping (leakage in Python 2 vs 3)

Data Structures:
    ```python
    @dataclass
    class NameReference:
        name: str
        node: ast.Name
        context: Literal["load", "store", "delete"]
        definition: PythonSymbol | None  # None if undefined
        scope: PythonScope
        line: int
        column: int
    ```

Test Cases:
    - Variable shadowing resolution
    - Import alias tracking
    - Undefined name detection
    - Walrus operator scope handling

==============================================================================
COMPLETED [P2-AST-005]: Call graph generation
==============================================================================
Priority: HIGH
Status: ✓ COMPLETED

Implemented Features:
    - [✓] Extract direct function calls (Name nodes in Call)
    - [✓] Track method calls with receiver identification
    - [✓] Handle chained calls (a.b().c())
    - [✓] Detect lambda and closure calls
    - [✓] Identify dynamic calls (getattr, eval, exec)
    - [✓] Track constructor calls (__init__, __new__)
    - [✓] Handle *args and **kwargs in calls
    - [✓] Identify import-based external calls
    - [✓] Detect recursive functions (direct and indirect)
    - [✓] Identify entry points and leaf functions

Data Structures:
    ```python
    @dataclass
    class CallSite:
        caller: PythonFunction
        callee_name: str  # May not be resolvable
        callee: PythonFunction | None  # None if external/dynamic
        args_count: int
        has_starargs: bool
        has_kwargs: bool
        line: int
        column: int

    @dataclass
    class CallGraph:
        nodes: set[PythonFunction]
        edges: list[CallSite]
        entry_points: set[PythonFunction]  # Functions not called internally
        leaf_functions: set[PythonFunction]  # Functions that make no calls
    ```

Test Cases:
    - Simple function call graph
    - Method calls on known classes
    - Dynamic getattr-based calls
    - Recursive function detection

==============================================================================
COMPLETED [P2-AST-006]: Control flow graph (CFG) generation
==============================================================================
Priority: HIGH
Status: ✓ COMPLETED

Implemented Features:
    - [✓] Create basic blocks from sequential statements
    - [✓] Handle branch nodes (if/elif/else)
    - [✓] Handle loop nodes (for, while)
    - [✓] Handle exception flow (try/except/finally/else)
    - [✓] Handle context managers (with statement)
    - [✓] Handle control flow jumps (return, raise, break, continue)
    - [✓] Handle match/case (Python 3.10+)
    - [—] Support assert with AssertionError path (out of scope - assert is sequential)
    - [✓] Path enumeration from entry to exit
    - [✓] Dominator and immediate dominator computation
    - [✓] Back edge detection for loops

Data Structures:
    ```python
    @dataclass
    class BasicBlock:
        id: int
        statements: list[ast.stmt]
        predecessors: list[BasicBlock]
        successors: list[BasicBlock]
        is_entry: bool = False
        is_exit: bool = False

    @dataclass
    class ControlFlowGraph:
        function: PythonFunction
        entry_block: BasicBlock
        exit_block: BasicBlock
        blocks: list[BasicBlock]

        def get_all_paths(self) -> Iterator[list[BasicBlock]]:
            '''Yield all paths from entry to exit.'''
            ...
    ```

Test Cases:
    - Simple if/else branching
    - Nested loops with break/continue
    - Try/except/finally paths
    - Match statement exhaustiveness

==============================================================================
COMPLETED [P2-AST-007]: Data flow analysis
==============================================================================
Priority: HIGH
Status: ✓ COMPLETED

Implemented Features:
    - [✓] Compute reaching definitions at each program point
    - [✓] Compute live variables at each program point
    - [✓] Build definition-use (def-use) chains
    - [✓] Build use-definition (use-def) chains
    - [✓] Basic constant propagation
    - [✓] Dead assignment detection
    - [✓] Available expressions analysis
    - [✓] Very busy expressions analysis
    - [✓] Undefined variable detection

Data Structures:
    ```python
    @dataclass
    class Definition:
        variable: str
        node: ast.AST
        block: BasicBlock

    @dataclass
    class DataFlowInfo:
        reaching_definitions: dict[BasicBlock, set[Definition]]
        live_variables: dict[BasicBlock, set[str]]
        def_use_chains: dict[Definition, set[ast.Name]]
        use_def_chains: dict[ast.Name, set[Definition]]
        dead_assignments: list[Definition]
    ```

Test Cases:
    - Variable overwritten before use (dead assignment)
    - Use before definition detection
    - Constant propagation through assignments
    - Live variable analysis at function boundaries

==============================================================================
COMPLETED [P2-AST-008]: Type annotation extraction
==============================================================================
Priority: HIGH
Status: ✓ COMPLETED

Implemented Features:
    - [✓] Extract PEP 484 function parameter/return annotations
    - [✓] Extract PEP 526 variable annotations
    - [✓] Handle PEP 604 union syntax (X | Y)
    - [✓] Handle string annotations (forward references)
    - [✓] Parse typing module generics (List[int], Dict[str, Any])
    - [—] Extract TypeVar definitions and bounds (out of scope - runtime construct)
    - [✓] Detect Protocol and Generic base classes
    - [—] Handle Annotated[X, metadata] (out of scope - requires runtime introspection)
    - [✓] Parse Optional, Union, Callable types
    - [✓] Parse Literal types with values
    - [✓] Extract all annotations from module

Data Structures:
    ```python
    @dataclass
    class TypeAnnotation:
        raw_annotation: str  # As written in source
        resolved_annotation: str | None  # After string eval
        is_optional: bool
        is_union: bool
        union_members: list[TypeAnnotation]
        is_generic: bool
        generic_params: list[TypeAnnotation]
        origin_type: str | None  # e.g., "list" for List[int]
    ```

Test Cases:
    - Simple type annotations (int, str)
    - Generic types (List[int], Dict[str, int])
    - Union types (int | str, Optional[int])
    - Forward references ("ClassName")
    - Complex nested generics
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    pass


# =============================================================================
# Enums
# =============================================================================


class SymbolKind(Enum):
    """Kind of symbol in the symbol table."""

    MODULE = auto()
    CLASS = auto()
    FUNCTION = auto()
    ASYNC_FUNCTION = auto()
    METHOD = auto()
    ASYNC_METHOD = auto()
    LAMBDA = auto()
    VARIABLE = auto()
    CONSTANT = auto()
    PARAMETER = auto()
    IMPORT = auto()
    IMPORT_FROM = auto()
    TYPE_ALIAS = auto()
    TYPE_VAR = auto()


class ScopeType(Enum):
    """Type of scope in Python."""

    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    ASYNC_FUNCTION = "async_function"
    COMPREHENSION = "comprehension"
    LAMBDA = "lambda"


class NameContext(Enum):
    """Context in which a name is used."""

    LOAD = "load"
    STORE = "store"
    DELETE = "delete"
    ANNOTATION = "annotation"


# =============================================================================
# Data Classes - Symbol Information
# =============================================================================


@dataclass
class SourceLocation:
    """Location in source code."""

    line: int
    column: int
    end_line: int | None = None
    end_column: int | None = None

    @classmethod
    def from_node(cls, node: ast.AST) -> SourceLocation:
        """Create from AST node."""
        return cls(
            line=getattr(node, "lineno", 0),
            column=getattr(node, "col_offset", 0),
            end_line=getattr(node, "end_lineno", None),
            end_column=getattr(node, "end_col_offset", None),
        )


@dataclass
class TypeAnnotation:
    """Represents a type annotation."""

    raw_annotation: str
    resolved_annotation: str | None = None
    is_optional: bool = False
    is_union: bool = False
    union_members: list[TypeAnnotation] = field(default_factory=list)
    is_generic: bool = False
    generic_params: list[TypeAnnotation] = field(default_factory=list)
    origin_type: str | None = None
    is_callable: bool = False
    callable_params: list[TypeAnnotation] = field(default_factory=list)
    callable_return: TypeAnnotation | None = None
    is_literal: bool = False
    literal_values: list[str] = field(default_factory=list)
    is_type_var: bool = False
    is_forward_ref: bool = False

    @classmethod
    def from_node(cls, node: ast.expr | None) -> TypeAnnotation | None:
        """
        Parse type annotation from AST node.

        Handles:
        - Simple types: int, str, MyClass
        - Generic types: List[int], Dict[str, int]
        - Union types: int | str, Union[int, str]
        - Optional types: Optional[int], int | None
        - Callable types: Callable[[int], str]
        - Literal types: Literal['a', 'b']
        - Forward references: 'MyClass'
        """
        if node is None:
            return None

        raw = ast.unparse(node)

        # Handle string annotations (forward references)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return cls(
                raw_annotation=raw,
                resolved_annotation=node.value,
                is_forward_ref=True,
            )

        # Handle Name (simple type)
        if isinstance(node, ast.Name):
            return cls(
                raw_annotation=raw,
                resolved_annotation=node.id,
                origin_type=node.id,
            )

        # Handle Attribute (qualified type like typing.List)
        if isinstance(node, ast.Attribute):
            return cls(
                raw_annotation=raw,
                resolved_annotation=raw,
                origin_type=raw,
            )

        # Handle Subscript (generic types)
        if isinstance(node, ast.Subscript):
            return cls._parse_subscript(node, raw)

        # Handle BinOp (union with |)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return cls._parse_union_binop(node, raw)

        # Handle Constant (for Literal values)
        if isinstance(node, ast.Constant):
            return cls(
                raw_annotation=raw,
                resolved_annotation=repr(node.value),
            )

        # Handle Tuple (for multiple types in Callable, etc.)
        if isinstance(node, ast.Tuple):
            params = [cls.from_node(elt) for elt in node.elts]
            return cls(
                raw_annotation=raw,
                generic_params=[p for p in params if p],
            )

        # Default: just store the raw annotation
        return cls(raw_annotation=raw)

    @classmethod
    def _parse_subscript(cls, node: ast.Subscript, raw: str) -> TypeAnnotation:
        """Parse a subscript (generic) type annotation."""
        # Get the origin type
        origin = ast.unparse(node.value)

        # Handle Union
        if origin in ("Union", "typing.Union"):
            return cls._parse_union(node.slice, raw)

        # Handle Optional
        if origin in ("Optional", "typing.Optional"):
            inner = cls.from_node(node.slice)
            return cls(
                raw_annotation=raw,
                is_optional=True,
                is_union=True,
                union_members=[inner] if inner else [],
                origin_type=origin,
            )

        # Handle Callable
        if origin in ("Callable", "typing.Callable", "collections.abc.Callable"):
            return cls._parse_callable(node.slice, raw, origin)

        # Handle Literal
        if origin in ("Literal", "typing.Literal"):
            return cls._parse_literal(node.slice, raw)

        # Handle generic container types
        inner_types = cls._parse_slice_elements(node.slice)
        return cls(
            raw_annotation=raw,
            is_generic=True,
            generic_params=inner_types,
            origin_type=origin,
        )

    @classmethod
    def _parse_union(cls, slice_node: ast.AST, raw: str) -> TypeAnnotation:
        """Parse Union type."""
        members = cls._parse_slice_elements(slice_node)
        is_optional = any(m.raw_annotation in ("None", "type(None)") or m.origin_type == "None" for m in members)
        return cls(
            raw_annotation=raw,
            is_union=True,
            is_optional=is_optional,
            union_members=members,
            origin_type="Union",
        )

    @classmethod
    def _parse_union_binop(cls, node: ast.BinOp, raw: str) -> TypeAnnotation:
        """Parse union using | operator."""
        members = []

        def collect_union_members(n: ast.AST) -> None:
            if isinstance(n, ast.BinOp) and isinstance(n.op, ast.BitOr):
                collect_union_members(n.left)
                collect_union_members(n.right)
            else:
                # Only process expr nodes (not generic AST)
                if isinstance(n, ast.expr):
                    parsed = cls.from_node(n)
                    if parsed:
                        members.append(parsed)

        collect_union_members(node)

        is_optional = any(m.raw_annotation == "None" or m.origin_type == "None" for m in members)

        return cls(
            raw_annotation=raw,
            is_union=True,
            is_optional=is_optional,
            union_members=members,
            origin_type="Union",
        )

    @classmethod
    def _parse_callable(cls, slice_node: ast.AST, raw: str, origin: str) -> TypeAnnotation:
        """Parse Callable type."""
        annotation = cls(
            raw_annotation=raw,
            is_callable=True,
            origin_type=origin,
        )

        if isinstance(slice_node, ast.Tuple) and len(slice_node.elts) >= 2:
            # First element is params, last is return type
            params_node = slice_node.elts[0]
            return_node = slice_node.elts[-1]

            # Parse params (can be a list or ellipsis)
            if isinstance(params_node, ast.List):
                annotation.callable_params = [
                    p for p in (cls.from_node(elem) for elem in params_node.elts) if p is not None
                ]
            elif isinstance(params_node, ast.Constant) and params_node.value == ...:
                annotation.callable_params = []  # Ellipsis means any params

            annotation.callable_return = cls.from_node(return_node)

        return annotation

    @classmethod
    def _parse_literal(cls, slice_node: ast.AST, raw: str) -> TypeAnnotation:
        """Parse Literal type."""
        values = []

        if isinstance(slice_node, ast.Tuple):
            for elt in slice_node.elts:
                if isinstance(elt, ast.Constant):
                    values.append(repr(elt.value))
        elif isinstance(slice_node, ast.Constant):
            values.append(repr(slice_node.value))

        return cls(
            raw_annotation=raw,
            is_literal=True,
            literal_values=values,
            origin_type="Literal",
        )

    @classmethod
    def _parse_slice_elements(cls, node: ast.AST) -> list[TypeAnnotation]:
        """Parse elements from a slice (handles both Tuple and single elements)."""
        if isinstance(node, ast.Tuple):
            result = []
            for elt in node.elts:
                parsed = cls.from_node(elt)
                if parsed:
                    result.append(parsed)
            return result
        else:
            # Only process expr nodes
            if isinstance(node, ast.expr):
                parsed = cls.from_node(node)
                return [parsed] if parsed else []
            return []


@dataclass
class PythonSymbol:
    """Represents a symbol in Python code."""

    name: str
    qualified_name: str
    kind: SymbolKind
    location: SourceLocation
    parent: PythonSymbol | None = None
    docstring: str | None = None
    decorators: list[str] = field(default_factory=list)
    type_annotation: TypeAnnotation | None = None
    is_private: bool = False  # Starts with _
    is_dunder: bool = False  # Starts and ends with __
    ast_node: ast.AST | None = field(default=None, repr=False)  # Store AST node for analysis


@dataclass
class PythonParameter:
    """Represents a function parameter."""

    name: str
    kind: Literal[
        "positional_only",
        "positional_or_keyword",
        "var_positional",
        "keyword_only",
        "var_keyword",
    ]
    default: str | None = None  # String representation of default value
    annotation: TypeAnnotation | None = None
    location: SourceLocation | None = None


@dataclass
class PythonFunction(PythonSymbol):
    """Represents a function or method."""

    parameters: list[PythonParameter] = field(default_factory=list)
    return_annotation: TypeAnnotation | None = None
    is_async: bool = False
    is_generator: bool = False  # Contains yield
    is_coroutine: bool = False  # async def
    is_staticmethod: bool = False
    is_classmethod: bool = False
    is_property: bool = False
    is_abstractmethod: bool = False
    raises: list[str] = field(default_factory=list)  # Exception types raised
    body_complexity: int = 0  # Cyclomatic complexity

    def __post_init__(self):
        if self.kind not in (
            SymbolKind.FUNCTION,
            SymbolKind.ASYNC_FUNCTION,
            SymbolKind.METHOD,
            SymbolKind.ASYNC_METHOD,
            SymbolKind.LAMBDA,
        ):
            self.kind = SymbolKind.FUNCTION


@dataclass
class PythonClass(PythonSymbol):
    """Represents a class definition."""

    bases: list[str] = field(default_factory=list)
    metaclass: str | None = None
    keywords: dict[str, str] = field(default_factory=dict)  # Other class kwargs
    methods: list[PythonFunction] = field(default_factory=list)
    class_variables: list[PythonSymbol] = field(default_factory=list)
    instance_variables: list[PythonSymbol] = field(default_factory=list)
    is_dataclass: bool = False
    is_namedtuple: bool = False
    is_protocol: bool = False
    is_abstract: bool = False
    slots: list[str] | None = None  # __slots__ if defined

    def __post_init__(self):
        self.kind = SymbolKind.CLASS


@dataclass
class PythonImport:
    """Represents an import statement."""

    module: str  # The module being imported
    name: str | None = None  # For "from X import name"
    alias: str | None = None  # The "as" alias
    is_from_import: bool = False
    is_relative: bool = False
    level: int = 0  # Number of dots for relative imports
    location: SourceLocation | None = None

    @property
    def imported_name(self) -> str:
        """Get the name that will be bound in the namespace."""
        if self.alias:
            return self.alias
        if self.is_from_import and self.name:
            return self.name
        # For "import foo.bar", only "foo" is bound
        return self.module.split(".")[0]


@dataclass
class PythonModule:
    """Represents a parsed Python module."""

    path: Path | None
    name: str
    docstring: str | None = None
    ast_tree: ast.Module | None = None

    # Symbols
    imports: list[PythonImport] = field(default_factory=list)
    functions: list[PythonFunction] = field(default_factory=list)
    classes: list[PythonClass] = field(default_factory=list)
    variables: list[PythonSymbol] = field(default_factory=list)
    type_aliases: list[PythonSymbol] = field(default_factory=list)  # TypeAlias definitions

    # Analysis results
    all_symbols: list[PythonSymbol] = field(default_factory=list)
    scope_tree: PythonScope | None = None
    errors: list[str] = field(default_factory=list)


# =============================================================================
# Data Classes - Scope Analysis
# =============================================================================


@dataclass
class PythonScope:
    """Represents a scope in Python code."""

    type: ScopeType
    name: str
    node: ast.AST | None = None
    parent: PythonScope | None = None
    children: list[PythonScope] = field(default_factory=list)

    # Names defined/used in this scope
    local_names: set[str] = field(default_factory=set)
    global_names: set[str] = field(default_factory=set)  # 'global x' declarations
    nonlocal_names: set[str] = field(default_factory=set)  # 'nonlocal x' declarations
    free_variables: set[str] = field(default_factory=set)  # From enclosing scope
    cell_variables: set[str] = field(default_factory=set)  # Referenced by nested

    # Symbol bindings
    symbols: dict[str, PythonSymbol] = field(default_factory=dict)


@dataclass
class NameReference:
    """Represents a reference to a name."""

    name: str
    node: ast.Name
    context: NameContext
    definition: PythonSymbol | None = None
    scope: PythonScope | None = None
    location: SourceLocation | None = None
    is_undefined: bool = False
    is_builtin: bool = False


# =============================================================================
# Data Classes - Control Flow Graph
# =============================================================================


@dataclass(eq=False)
class BasicBlock:
    """Represents a basic block in a CFG."""

    id: int
    label: str = ""
    statements: list[ast.stmt] = field(default_factory=list)
    predecessors: list[BasicBlock] = field(default_factory=list)
    successors: list[BasicBlock] = field(default_factory=list)
    is_entry: bool = False
    is_exit: bool = False
    is_exception_handler: bool = False
    exception_type: str | None = None

    def __hash__(self) -> int:
        """Hash based on block id."""
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Equality based on block id."""
        if isinstance(other, BasicBlock):
            return self.id == other.id
        return False


@dataclass
class ControlFlowGraph:
    """Control flow graph for a function."""

    function: PythonFunction
    entry_block: BasicBlock | None = None
    exit_block: BasicBlock | None = None
    blocks: list[BasicBlock] = field(default_factory=list)

    def get_all_paths(self, max_paths: int = 1000) -> Iterator[list[BasicBlock]]:
        """
        Yield all paths from entry to exit.

        Uses depth-first search with cycle detection.
        Limited to max_paths to avoid infinite loops in pathological cases.

        Args:
            max_paths: Maximum number of paths to yield.

        Yields:
            Lists of BasicBlocks representing paths from entry to exit.
        """
        if not self.entry_block or not self.exit_block:
            return

        path_count = 0
        stack: list[tuple[BasicBlock, list[BasicBlock], set[int]]] = [
            (self.entry_block, [self.entry_block], {self.entry_block.id})
        ]

        while stack and path_count < max_paths:
            current, path, visited = stack.pop()

            if current.id == self.exit_block.id:
                yield path.copy()
                path_count += 1
                continue

            for succ in current.successors:
                if succ.id not in visited:
                    new_path = path + [succ]
                    new_visited = visited | {succ.id}
                    stack.append((succ, new_path, new_visited))

    def get_dominators(self) -> dict[int, set[int]]:
        """
        Compute dominator sets for each block.

        Block A dominates block B if every path from entry to B
        goes through A.

        Returns:
            Dictionary mapping block id to set of dominating block ids.
        """
        if not self.entry_block:
            return {}

        # Initialize: entry dominated only by itself, others by all blocks
        all_block_ids = {b.id for b in self.blocks}
        dominators: dict[int, set[int]] = {}

        for block in self.blocks:
            if block.id == self.entry_block.id:
                dominators[block.id] = {block.id}
            else:
                dominators[block.id] = all_block_ids.copy()

        # Build id -> block mapping
        {b.id: b for b in self.blocks}

        # Iterate until no changes
        changed = True
        while changed:
            changed = False
            for block in self.blocks:
                if block.id == self.entry_block.id:
                    continue

                # Dom(b) = {b} ∪ ⋂ Dom(p) for all predecessors p
                if block.predecessors:
                    pred_doms = [dominators[p.id] for p in block.predecessors]
                    new_dom = {block.id} | set.intersection(*pred_doms)
                else:
                    new_dom = {block.id}

                if new_dom != dominators[block.id]:
                    dominators[block.id] = new_dom
                    changed = True

        return dominators

    def get_immediate_dominators(self) -> dict[int, int | None]:
        """
        Compute immediate dominators for each block.

        The immediate dominator of B is the closest strict dominator of B.

        Returns:
            Dictionary mapping block id to immediate dominator block id (None for entry).
        """
        dominators = self.get_dominators()
        idom: dict[int, int | None] = {}

        for block_id, doms in dominators.items():
            strict_doms = doms - {block_id}
            if not strict_doms:
                idom[block_id] = None  # Entry block
            else:
                # Find the dominator closest to block (dominated by all others)
                for dom_id in strict_doms:
                    if all(dom_id in dominators[other] or other == dom_id for other in strict_doms):
                        idom[block_id] = dom_id
                        break

        return idom

    def get_back_edges(self) -> list[tuple[int, int]]:
        """
        Find back edges in the CFG (edges to a dominator).

        Back edges indicate loops.

        Returns:
            List of (from_block_id, to_block_id) tuples representing back edges.
        """
        dominators = self.get_dominators()
        back_edges = []

        for block in self.blocks:
            for succ in block.successors:
                if succ.id in dominators.get(block.id, set()):
                    back_edges.append((block.id, succ.id))

        return back_edges


# =============================================================================
# Data Classes - Call Graph
# =============================================================================


@dataclass
class CallSite:
    """Represents a function call site."""

    caller: PythonFunction
    callee_name: str
    callee: PythonFunction | None = None  # None if unresolved
    receiver: str | None = None  # For method calls
    args_count: int = 0
    has_starargs: bool = False
    has_kwargs: bool = False
    is_dynamic: bool = False  # getattr, eval, etc.
    location: SourceLocation | None = None


@dataclass
class CallGraph:
    """Call graph for a module or set of modules."""

    # Using lists instead of sets because PythonFunction has mutable fields
    # We use id() for comparison when needed
    nodes: list[PythonFunction] = field(default_factory=list)
    edges: list[CallSite] = field(default_factory=list)
    entry_points: list[PythonFunction] = field(default_factory=list)
    leaf_functions: list[PythonFunction] = field(default_factory=list)
    recursive_functions: list[PythonFunction] = field(default_factory=list)

    # Internal id-based tracking
    _node_ids: set[int] = field(default_factory=set, repr=False)

    def add_node(self, func: PythonFunction) -> None:
        """Add a function node to the graph."""
        func_id = id(func)
        if func_id not in self._node_ids:
            self._node_ids.add(func_id)
            self.nodes.append(func)

    def has_node(self, func: PythonFunction) -> bool:
        """Check if a function is in the graph."""
        return id(func) in self._node_ids

    def get_callers(self, func: PythonFunction) -> list[PythonFunction]:
        """Get all functions that call the given function."""
        func_id = id(func)
        return [edge.caller for edge in self.edges if edge.callee and id(edge.callee) == func_id]

    def get_callees(self, func: PythonFunction) -> list[PythonFunction]:
        """Get all functions called by the given function."""
        caller_id = id(func)
        return [edge.callee for edge in self.edges if id(edge.caller) == caller_id and edge.callee is not None]


# =============================================================================
# Data Classes - Data Flow Analysis
# =============================================================================


@dataclass(eq=False)
class Definition:
    """Represents a variable definition."""

    variable: str
    node: ast.AST | None  # None for parameters
    block: BasicBlock | None = None
    is_parameter: bool = False
    is_global: bool = False
    is_nonlocal: bool = False

    def __hash__(self) -> int:
        """Hash based on identity."""
        return id(self)

    def __eq__(self, other: object) -> bool:
        """Equality based on identity."""
        return self is other


@dataclass(frozen=True)
class Expression:
    """Represents an expression for available/busy expression analysis."""

    expr_str: str  # Canonical string representation
    variables: frozenset[str]  # Variables used in the expression

    @classmethod
    def from_node(cls, node: ast.expr) -> Expression:
        """Create an Expression from an AST node."""
        expr_str = ast.unparse(node)
        variables = frozenset(n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load))
        return cls(expr_str=expr_str, variables=variables)

    def is_killed_by(self, defined_var: str) -> bool:
        """Check if this expression is killed by defining a variable."""
        return defined_var in self.variables


class ConstantValue:
    """Represents a constant value or non-constant state."""

    __slots__ = ("_value", "_is_constant")

    # Sentinel for non-constant (Top in lattice)
    NAC = object()  # Not A Constant
    # Sentinel for undefined (Bottom in lattice)
    UNDEF = object()

    def __init__(self, value: object = None, is_constant: bool = True):
        self._value = value
        self._is_constant = is_constant

    @classmethod
    def constant(cls, value: object) -> ConstantValue:
        """Create a constant value."""
        return cls(value, True)

    @classmethod
    def not_constant(cls) -> ConstantValue:
        """Create a non-constant value (NAC)."""
        return cls(cls.NAC, False)

    @classmethod
    def undefined(cls) -> ConstantValue:
        """Create an undefined value."""
        return cls(cls.UNDEF, False)

    @property
    def is_constant(self) -> bool:
        return self._is_constant and self._value is not self.NAC and self._value is not self.UNDEF

    @property
    def value(self) -> object:
        if not self.is_constant:
            raise ValueError("Value is not constant")
        return self._value

    def meet(self, other: ConstantValue) -> ConstantValue:
        """Lattice meet operation for constant propagation."""
        # UNDEF meet x = x
        if self._value is self.UNDEF:
            return other
        if other._value is self.UNDEF:
            return self
        # NAC meet x = NAC
        if self._value is self.NAC or other._value is self.NAC:
            return ConstantValue.not_constant()
        # c1 meet c2 = c1 if c1 == c2 else NAC
        if self._value == other._value:
            return self
        return ConstantValue.not_constant()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ConstantValue):
            return False
        return self._value == other._value and self._is_constant == other._is_constant

    def __hash__(self) -> int:
        return hash(
            (
                self._is_constant,
                (id(self._value) if self._value in (self.NAC, self.UNDEF) else self._value),
            )
        )

    def __repr__(self) -> str:
        if self._value is self.NAC:
            return "ConstantValue(NAC)"
        if self._value is self.UNDEF:
            return "ConstantValue(UNDEF)"
        return f"ConstantValue({self._value!r})"


@dataclass
class DataFlowInfo:
    """Data flow analysis results."""

    reaching_definitions: dict[BasicBlock, set[Definition]] = field(default_factory=dict)
    live_variables: dict[BasicBlock, set[str]] = field(default_factory=dict)
    def_use_chains: dict[Definition, set[ast.Name]] = field(default_factory=dict)
    use_def_chains: dict[int, set[Definition]] = field(default_factory=dict)  # node id -> definitions
    dead_assignments: list[Definition] = field(default_factory=list)
    undefined_uses: list[ast.Name] = field(default_factory=list)
    # Optimization analyses
    constant_values: dict[BasicBlock, dict[str, ConstantValue]] = field(default_factory=dict)
    available_expressions: dict[BasicBlock, set[Expression]] = field(default_factory=dict)
    very_busy_expressions: dict[BasicBlock, set[Expression]] = field(default_factory=dict)


# =============================================================================
# Main Parser Class
# =============================================================================


class PythonASTParser:
    """
    Comprehensive Python AST parser and analyzer.

    This parser provides:
    - Full AST parsing with error recovery
    - Symbol table generation
    - Scope analysis (LEGB)
    - Name binding and resolution
    - Call graph generation
    - Control flow graph generation
    - Data flow analysis

    Implemented:
    - [✓] P1-AST-001: Comprehensive node visitor with parent tracking
    - [✓] P1-AST-002: Symbol table generation
    - [✓] P1-AST-003: Scope analysis (LEGB)
    - [✓] P1-AST-004: Name binding and resolution
    - [✓] P2-AST-005: Call graph generation
    - [✓] P2-AST-006: Control flow graph generation
    - [✓] P2-AST-007: Data flow analysis
    - [✓] P2-AST-008: Type annotation extraction
    """

    def __init__(self, *, include_type_comments: bool = True):
        """
        Initialize the parser.

        Args:
            include_type_comments: Whether to parse type comments (# type: ...)
        """
        self.include_type_comments = include_type_comments
        self._builtin_names: set[str] = (
            set(dir(__builtins__)) if isinstance(__builtins__, dict) else set(dir(__builtins__))
        )

    def parse_file(self, path: str | Path) -> PythonModule:
        """
        Parse a Python file.

        Args:
            path: Path to the Python file.

        Returns:
            PythonModule with parsed information.
        """
        path = Path(path)
        source = path.read_text(encoding="utf-8")
        return self.parse_string(source, filename=str(path), module_name=path.stem)

    def parse_string(
        self,
        source: str,
        *,
        filename: str = "<string>",
        module_name: str = "<module>",
    ) -> PythonModule:
        """
        Parse Python source code from a string.

        Args:
            source: Python source code.
            filename: Filename for error messages.
            module_name: Name of the module.

        Returns:
            PythonModule with parsed information.
        """
        module = PythonModule(
            path=Path(filename) if filename != "<string>" else None,
            name=module_name,
        )

        try:
            tree = ast.parse(
                source,
                filename=filename,
                type_comments=self.include_type_comments,
            )
            module.ast_tree = tree
            module.docstring = ast.get_docstring(tree)

            # Extract symbols (P1-AST-002)
            source_lines = source.splitlines()
            self._extract_symbols(tree, module, source_lines)

            # Analyze scopes (P1-AST-003)
            module.scope_tree = self._analyze_scopes(tree, module_name)

        except SyntaxError as e:
            module.errors.append(f"SyntaxError at line {e.lineno}: {e.msg}")
            # Try partial recovery
            self._try_partial_parse(source, module, filename)

        return module

    def _try_partial_parse(
        self,
        source: str,
        module: PythonModule,
        filename: str,
    ) -> None:
        """
        Try to parse as much as possible from source with syntax errors.

        This attempts line-by-line parsing to recover partial AST.
        """
        lines = source.splitlines()
        recovered_source: list[str] = []

        for _i, line in enumerate(lines):
            test_source = "\n".join(recovered_source + [line])
            try:
                ast.parse(test_source, filename=filename)
                recovered_source.append(line)
            except SyntaxError:
                # Skip this line, try with placeholder
                recovered_source.append("pass  # ERROR: syntax error on this line")

        if recovered_source:
            try:
                tree = ast.parse("\n".join(recovered_source), filename=filename)
                module.ast_tree = tree
                self._extract_symbols(tree, module, recovered_source)
            except SyntaxError:
                pass  # Give up on partial recovery

    def _extract_symbols(
        self,
        tree: ast.Module,
        module: PythonModule,
        source_lines: list[str],
    ) -> None:
        """
        Extract all symbols from the AST.

        Implements P1-AST-002: Symbol table generation.
        """
        visitor = SymbolVisitor(module, source_lines)
        visitor.visit(tree)
        module.all_symbols = visitor._all_symbols

    def _analyze_scopes(self, tree: ast.Module, module_name: str) -> PythonScope:
        """
        Analyze scopes in the AST.

        Implements P1-AST-003: Scope analysis (LEGB).
        """
        analyzer = ScopeAnalyzer()
        return analyzer.analyze(tree, module_name)

    def extract_symbols(self, module: PythonModule) -> None:
        """
        Extract all symbols from a parsed module.

        This is called automatically by parse_* methods.
        Use this only if you need to re-extract symbols.
        """
        if module.ast_tree is None:
            return

        source_lines: list[str] = []
        if module.path:
            source_lines = module.path.read_text().splitlines()

        self._extract_symbols(module.ast_tree, module, source_lines)

    def analyze_scopes(self, module: PythonModule) -> PythonScope:
        """
        Analyze scopes in a parsed module.

        This is called automatically by parse_* methods.
        """
        if module.ast_tree is None:
            raise ValueError("Module has no AST")

        return self._analyze_scopes(module.ast_tree, module.name)

    def resolve_names(self, module: PythonModule) -> list[NameReference]:
        """
        Resolve all name references in a module.

        Implements P1-AST-004: Name binding and reference resolution.

        Args:
            module: A parsed PythonModule (must have scope_tree populated).

        Returns:
            List of NameReference objects with resolved definitions.
        """
        if module.ast_tree is None:
            raise ValueError("Module has no AST")
        if module.scope_tree is None:
            module.scope_tree = self._analyze_scopes(module.ast_tree, module.name)

        resolver = NameResolver(module.scope_tree, module.all_symbols)
        return resolver.resolve(module.ast_tree)

    def get_undefined_names(self, module: PythonModule) -> list[NameReference]:
        """
        Get all undefined name references in a module.

        Args:
            module: A parsed PythonModule.

        Returns:
            List of NameReference objects that are undefined.
        """
        references = self.resolve_names(module)
        return [ref for ref in references if ref.is_undefined]

    def build_call_graph(self, module: PythonModule) -> CallGraph:
        """
        Build a call graph for a module.

        Implements P2-AST-005: Call graph generation.

        The call graph shows which functions call which other functions.
        It identifies:
        - Direct function calls
        - Method calls (with receiver tracking)
        - Entry points (functions not called by others)
        - Leaf functions (functions that don't call anything)
        - Recursive functions

        Args:
            module: A parsed PythonModule.

        Returns:
            CallGraph with nodes (functions) and edges (call sites).
        """
        if module.ast_tree is None:
            raise ValueError("Module has no AST")

        builder = CallGraphBuilder(module)
        return builder.build(module.ast_tree)

    def build_cfg(self, function: PythonFunction, source: str | None = None) -> ControlFlowGraph:
        """
        Build a control flow graph for a function.

        Implements P2-AST-006: CFG generation.

        The CFG represents possible execution paths through a function:
        - Basic blocks contain sequential statements
        - Edges show control flow between blocks
        - Entry and exit blocks are marked
        - Loop headers and exit points are tracked
        - Exception handlers are identified

        Args:
            function: A PythonFunction from a parsed module.
            source: Optional source code (for re-parsing if needed).

        Returns:
            ControlFlowGraph with basic blocks and edges.
        """
        # We need the AST node for the function
        if function.ast_node is None:
            raise ValueError(f"Function {function.name} has no AST node")

        # Type guard: ensure ast_node is a function definition
        if not isinstance(function.ast_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            raise ValueError(f"Expected FunctionDef or AsyncFunctionDef, got {type(function.ast_node)}")

        builder = CFGBuilder(function)
        return builder.build(function.ast_node)

    def analyze_data_flow(self, cfg: ControlFlowGraph) -> DataFlowInfo:
        """
        Perform data flow analysis on a control flow graph.

        Implements P2-AST-007: Data flow analysis.

        Computes:
        - Reaching definitions for each basic block
        - Live variables at each basic block
        - Def-use chains (which uses depend on which definitions)
        - Use-def chains (which definitions can reach each use)
        - Dead assignments (definitions never used)
        - Undefined uses (uses with no reaching definition)

        Args:
            cfg: A ControlFlowGraph from build_cfg().

        Returns:
            DataFlowInfo with analysis results.
        """
        analyzer = DataFlowAnalyzer(cfg, cfg.function)
        return analyzer.analyze()

    def extract_type_annotations(self, module: PythonModule) -> dict[str, TypeAnnotation]:
        """
        Extract all type annotations from a module.

        Implements P2-AST-008: Type annotation extraction.

        Collects type annotations from:
        - Function parameters and return types
        - Variable annotations (module-level and in functions)
        - Class attributes (class_variables, instance_variables)
        - Type aliases

        Args:
            module: A parsed PythonModule.

        Returns:
            Dictionary mapping qualified names to TypeAnnotation objects.
        """
        annotations: dict[str, TypeAnnotation] = {}

        # Extract from functions
        for func in module.functions:
            func_qname = func.qualified_name

            # Return type
            if func.return_annotation:
                annotations[f"{func_qname}:return"] = func.return_annotation

            # Parameter types
            for param in func.parameters:
                if param.annotation:
                    annotations[f"{func_qname}:{param.name}"] = param.annotation

        # Extract from classes
        for cls in module.classes:
            cls_qname = cls.qualified_name

            # Method annotations
            for method in cls.methods:
                method_qname = method.qualified_name

                if method.return_annotation:
                    annotations[f"{method_qname}:return"] = method.return_annotation

                for param in method.parameters:
                    if param.annotation:
                        annotations[f"{method_qname}:{param.name}"] = param.annotation

            # Class variable annotations
            for var in cls.class_variables:
                if var.type_annotation:
                    annotations[f"{cls_qname}.{var.name}"] = var.type_annotation

            # Instance variable annotations
            for var in cls.instance_variables:
                if var.type_annotation:
                    annotations[f"{cls_qname}.{var.name}"] = var.type_annotation

        # Extract from module-level variable annotations
        for var in module.variables:
            if var.type_annotation:
                annotations[var.qualified_name] = var.type_annotation

        # Extract type aliases
        for alias in module.type_aliases:
            if alias.type_annotation:
                annotations[alias.qualified_name] = alias.type_annotation

        return annotations


# =============================================================================
# Visitor Classes - P1-AST-001: Comprehensive Node Visitor
# =============================================================================


class ParentTrackingVisitor(ast.NodeVisitor):
    """
    Base visitor that tracks parent-child relationships in AST.

    Implements P1-AST-001: Comprehensive node visitor with parent tracking.
    """

    def __init__(self):
        self.parent_stack: list[ast.AST] = []
        self.node_parents: dict[int, ast.AST | None] = {}  # node id -> parent
        self.node_children: dict[int, list[ast.AST]] = {}  # node id -> children

    def visit(self, node: ast.AST) -> Any:
        """Visit a node, tracking parent relationship."""
        node_id = id(node)
        parent = self.parent_stack[-1] if self.parent_stack else None
        self.node_parents[node_id] = parent

        if parent is not None:
            parent_id = id(parent)
            if parent_id not in self.node_children:
                self.node_children[parent_id] = []
            self.node_children[parent_id].append(node)

        self.parent_stack.append(node)
        result = super().visit(node)
        self.parent_stack.pop()
        return result

    def get_parent(self, node: ast.AST) -> ast.AST | None:
        """Get the parent of a node."""
        return self.node_parents.get(id(node))

    def get_ancestors(self, node: ast.AST) -> list[ast.AST]:
        """Get all ancestors of a node (parent, grandparent, etc.)."""
        ancestors = []
        current = self.get_parent(node)
        while current is not None:
            ancestors.append(current)
            current = self.get_parent(current)
        return ancestors

    def get_children(self, node: ast.AST) -> list[ast.AST]:
        """Get direct children of a node."""
        return self.node_children.get(id(node), [])


class SymbolVisitor(ParentTrackingVisitor):
    """
    Visitor for extracting symbols from AST.

    Implements P1-AST-002: Symbol table generation.
    """

    def __init__(self, module: PythonModule, source_lines: list[str] | None = None):
        super().__init__()
        self.module = module
        self.source_lines = source_lines or []
        self.scope_stack: list[PythonSymbol | None] = [None]  # Current parent symbol
        self._all_symbols: list[PythonSymbol] = []

    def _get_qualified_name(self, name: str) -> str:
        """Build qualified name from scope stack."""
        parts = []
        for scope in self.scope_stack:
            if scope is not None:
                parts.append(scope.name)
        parts.append(name)
        return ".".join(parts)

    def _get_decorators(self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> list[str]:
        """Extract decorator names from a node."""
        decorators = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                decorators.append(dec.id)
            elif isinstance(dec, ast.Attribute):
                decorators.append(ast.unparse(dec))
            elif isinstance(dec, ast.Call):
                if isinstance(dec.func, ast.Name):
                    decorators.append(dec.func.id)
                elif isinstance(dec.func, ast.Attribute):
                    decorators.append(ast.unparse(dec.func))
                else:
                    decorators.append(ast.unparse(dec))
            else:
                decorators.append(ast.unparse(dec))
        return decorators

    def _extract_parameters(self, args: ast.arguments) -> list[PythonParameter]:
        """Extract function parameters from arguments node."""
        params: list[PythonParameter] = []

        # Positional-only parameters (before /)
        for i, arg in enumerate(args.posonlyargs):
            default_idx = i - (len(args.posonlyargs) - len(args.defaults) + len(args.args))
            default = None
            if default_idx >= 0 and default_idx < len(args.defaults):
                default = ast.unparse(args.defaults[default_idx])

            params.append(
                PythonParameter(
                    name=arg.arg,
                    kind="positional_only",
                    default=default,
                    annotation=TypeAnnotation.from_node(arg.annotation),
                    location=(SourceLocation.from_node(arg) if hasattr(arg, "lineno") else None),
                )
            )

        # Regular positional or keyword parameters
        for i, arg in enumerate(args.args):
            default_idx = i - (len(args.args) - len(args.defaults))
            default = None
            if default_idx >= 0:
                default = ast.unparse(args.defaults[default_idx])

            params.append(
                PythonParameter(
                    name=arg.arg,
                    kind="positional_or_keyword",
                    default=default,
                    annotation=TypeAnnotation.from_node(arg.annotation),
                    location=(SourceLocation.from_node(arg) if hasattr(arg, "lineno") else None),
                )
            )

        # *args
        if args.vararg:
            params.append(
                PythonParameter(
                    name=args.vararg.arg,
                    kind="var_positional",
                    annotation=TypeAnnotation.from_node(args.vararg.annotation),
                    location=(SourceLocation.from_node(args.vararg) if hasattr(args.vararg, "lineno") else None),
                )
            )

        # Keyword-only parameters
        for i, arg in enumerate(args.kwonlyargs):
            default = None
            if i < len(args.kw_defaults) and args.kw_defaults[i] is not None:
                kw_default = args.kw_defaults[i]
                if isinstance(kw_default, ast.expr):
                    default = ast.unparse(kw_default)

            params.append(
                PythonParameter(
                    name=arg.arg,
                    kind="keyword_only",
                    default=default,
                    annotation=TypeAnnotation.from_node(arg.annotation),
                    location=(SourceLocation.from_node(arg) if hasattr(arg, "lineno") else None),
                )
            )

        # **kwargs
        if args.kwarg:
            params.append(
                PythonParameter(
                    name=args.kwarg.arg,
                    kind="var_keyword",
                    annotation=TypeAnnotation.from_node(args.kwarg.annotation),
                    location=(SourceLocation.from_node(args.kwarg) if hasattr(args.kwarg, "lineno") else None),
                )
            )

        return params

    def _check_function_properties(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, bool]:
        """Check function decorators for properties."""
        props = {
            "is_staticmethod": False,
            "is_classmethod": False,
            "is_property": False,
            "is_abstractmethod": False,
        }
        for dec in node.decorator_list:
            name = None
            if isinstance(dec, ast.Name):
                name = dec.id
            elif isinstance(dec, ast.Attribute):
                name = dec.attr

            if name == "staticmethod":
                props["is_staticmethod"] = True
            elif name == "classmethod":
                props["is_classmethod"] = True
            elif name == "property":
                props["is_property"] = True
            elif name == "abstractmethod":
                props["is_abstractmethod"] = True
        return props

    def _check_generator(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        """Check if function is a generator (contains yield)."""
        for child in ast.walk(node):
            if isinstance(child, (ast.Yield, ast.YieldFrom)):
                return True
        return False

    def _extract_raises(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
        """Extract exception types raised by function."""
        raises = []
        for child in ast.walk(node):
            if isinstance(child, ast.Raise) and child.exc:
                if isinstance(child.exc, ast.Call):
                    if isinstance(child.exc.func, ast.Name):
                        raises.append(child.exc.func.id)
                    elif isinstance(child.exc.func, ast.Attribute):
                        raises.append(ast.unparse(child.exc.func))
                elif isinstance(child.exc, ast.Name):
                    raises.append(child.exc.id)
        return list(set(raises))

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit a function definition."""
        is_method = isinstance(self.scope_stack[-1], PythonClass) if self.scope_stack[-1] else False
        props = self._check_function_properties(node)

        kind = SymbolKind.METHOD if is_method else SymbolKind.FUNCTION

        func = PythonFunction(
            name=node.name,
            qualified_name=self._get_qualified_name(node.name),
            kind=kind,
            location=SourceLocation.from_node(node),
            parent=self.scope_stack[-1],
            docstring=ast.get_docstring(node),
            decorators=self._get_decorators(node),
            parameters=self._extract_parameters(node.args),
            return_annotation=TypeAnnotation.from_node(node.returns),
            is_async=False,
            is_generator=self._check_generator(node),
            raises=self._extract_raises(node),
            is_private=is_private(node.name),
            is_dunder=is_dunder(node.name),
            ast_node=node,  # Store AST node for CFG analysis
            is_staticmethod=props["is_staticmethod"],
            is_classmethod=props["is_classmethod"],
            is_property=props["is_property"],
            is_abstractmethod=props["is_abstractmethod"],
        )

        self._all_symbols.append(func)
        self.module.functions.append(func)

        # Visit children with this function as the scope
        self.scope_stack.append(func)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit an async function definition."""
        is_method = isinstance(self.scope_stack[-1], PythonClass) if self.scope_stack[-1] else False
        props = self._check_function_properties(node)

        kind = SymbolKind.ASYNC_METHOD if is_method else SymbolKind.ASYNC_FUNCTION

        func = PythonFunction(
            name=node.name,
            qualified_name=self._get_qualified_name(node.name),
            kind=kind,
            location=SourceLocation.from_node(node),
            parent=self.scope_stack[-1],
            docstring=ast.get_docstring(node),
            decorators=self._get_decorators(node),
            parameters=self._extract_parameters(node.args),
            return_annotation=TypeAnnotation.from_node(node.returns),
            is_async=True,
            is_coroutine=True,
            is_generator=self._check_generator(node),
            raises=self._extract_raises(node),
            is_private=is_private(node.name),
            is_dunder=is_dunder(node.name),
            ast_node=node,  # Store AST node for CFG analysis
            is_staticmethod=props["is_staticmethod"],
            is_classmethod=props["is_classmethod"],
            is_property=props["is_property"],
            is_abstractmethod=props["is_abstractmethod"],
        )

        self._all_symbols.append(func)
        self.module.functions.append(func)

        self.scope_stack.append(func)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit a class definition."""
        bases = [ast.unparse(base) for base in node.bases]

        metaclass = None
        keywords = {}
        for kw in node.keywords:
            if kw.arg == "metaclass":
                metaclass = ast.unparse(kw.value)
            elif kw.arg:
                keywords[kw.arg] = ast.unparse(kw.value)

        # Check for special class types
        decorators = self._get_decorators(node)
        is_dataclass = "dataclass" in decorators
        is_protocol = "Protocol" in bases
        is_abstract = "ABC" in bases or "ABCMeta" == metaclass

        # Check for __slots__
        slots = None
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == "__slots__":
                        if isinstance(item.value, (ast.List, ast.Tuple)):
                            slots = []
                            for elt in item.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    slots.append(elt.value)

        cls = PythonClass(
            name=node.name,
            qualified_name=self._get_qualified_name(node.name),
            kind=SymbolKind.CLASS,
            location=SourceLocation.from_node(node),
            parent=self.scope_stack[-1],
            docstring=ast.get_docstring(node),
            decorators=decorators,
            bases=bases,
            metaclass=metaclass,
            keywords=keywords,
            is_dataclass=is_dataclass,
            is_protocol=is_protocol,
            is_abstract=is_abstract,
            slots=slots,
            is_private=is_private(node.name),
            is_dunder=is_dunder(node.name),
        )

        self._all_symbols.append(cls)
        self.module.classes.append(cls)

        # Visit children with this class as the scope
        self.scope_stack.append(cls)
        self.generic_visit(node)
        self.scope_stack.pop()

        # Collect methods and variables from visited children
        for sym in self._all_symbols:
            if sym.parent == cls:
                if isinstance(sym, PythonFunction):
                    cls.methods.append(sym)

    def visit_Import(self, node: ast.Import) -> None:
        """Visit an import statement."""
        for alias in node.names:
            imp = PythonImport(
                module=alias.name,
                alias=alias.asname,
                is_from_import=False,
                location=SourceLocation.from_node(node),
            )
            self.module.imports.append(imp)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit a from...import statement."""
        module = node.module or ""
        for alias in node.names:
            imp = PythonImport(
                module=module,
                name=alias.name,
                alias=alias.asname,
                is_from_import=True,
                is_relative=node.level > 0,
                level=node.level,
                location=SourceLocation.from_node(node),
            )
            self.module.imports.append(imp)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit an assignment statement."""
        # Only track module-level or class-level variables
        parent = self.scope_stack[-1]
        if parent is None or isinstance(parent, PythonClass):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    # Check if it's a constant (ALL_CAPS)
                    is_const = target.id.isupper() and "_" in target.id or target.id.isupper()
                    kind = SymbolKind.CONSTANT if is_const else SymbolKind.VARIABLE

                    sym = PythonSymbol(
                        name=target.id,
                        qualified_name=self._get_qualified_name(target.id),
                        kind=kind,
                        location=SourceLocation.from_node(target),
                        parent=parent,
                        is_private=is_private(target.id),
                        is_dunder=is_dunder(target.id),
                    )
                    self._all_symbols.append(sym)

                    if parent is None:
                        self.module.variables.append(sym)
                    elif isinstance(parent, PythonClass):
                        parent.class_variables.append(sym)

        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Visit an annotated assignment statement."""
        parent = self.scope_stack[-1]
        if parent is None or isinstance(parent, PythonClass):
            if isinstance(node.target, ast.Name):
                is_const = node.target.id.isupper()
                kind = SymbolKind.CONSTANT if is_const else SymbolKind.VARIABLE

                sym = PythonSymbol(
                    name=node.target.id,
                    qualified_name=self._get_qualified_name(node.target.id),
                    kind=kind,
                    location=SourceLocation.from_node(node.target),
                    parent=parent,
                    type_annotation=TypeAnnotation.from_node(node.annotation),
                    is_private=is_private(node.target.id),
                    is_dunder=is_dunder(node.target.id),
                )
                self._all_symbols.append(sym)

                if parent is None:
                    self.module.variables.append(sym)
                elif isinstance(parent, PythonClass):
                    parent.class_variables.append(sym)

        self.generic_visit(node)


class ScopeAnalyzer(ParentTrackingVisitor):
    """
    Visitor for analyzing scopes.

    Implements P1-AST-003: Scope analysis (LEGB rule).
    """

    def __init__(self):
        super().__init__()
        self.root_scope: PythonScope | None = None
        self.current_scope: PythonScope | None = None
        self.scope_stack: list[PythonScope] = []

    def _push_scope(self, scope_type: ScopeType, name: str, node: ast.AST) -> PythonScope:
        """Create and push a new scope."""
        parent = self.scope_stack[-1] if self.scope_stack else None
        scope = PythonScope(
            type=scope_type,
            name=name,
            node=node,
            parent=parent,
        )
        if parent:
            parent.children.append(scope)
        self.scope_stack.append(scope)
        self.current_scope = scope
        return scope

    def _pop_scope(self) -> PythonScope | None:
        """Pop the current scope."""
        if self.scope_stack:
            scope = self.scope_stack.pop()
            self.current_scope = self.scope_stack[-1] if self.scope_stack else None
            return scope
        return None

    def _add_local_name(self, name: str) -> None:
        """Add a name to the current scope's local names."""
        if self.current_scope:
            self.current_scope.local_names.add(name)

    def analyze(self, tree: ast.Module, module_name: str) -> PythonScope:
        """Analyze scopes in an AST."""
        self.root_scope = self._push_scope(ScopeType.MODULE, module_name, tree)
        self.visit(tree)
        self._pop_scope()

        # Post-process to identify free and cell variables
        self._compute_free_and_cell_variables(self.root_scope)

        return self.root_scope

    def _compute_free_and_cell_variables(self, scope: PythonScope) -> set[str]:
        """
        Compute free and cell variables for a scope.

        Free variables: referenced but not defined locally (come from enclosing scope)
        Cell variables: defined locally but referenced by nested scopes
        """
        # Recursively process children first
        child_free_vars: set[str] = set()
        for child in scope.children:
            child_free = self._compute_free_and_cell_variables(child)
            child_free_vars.update(child_free)

        # Variables referenced by children that we define locally are cell variables
        for var in child_free_vars:
            if var in scope.local_names:
                scope.cell_variables.add(var)

        # Free variables are those in child_free_vars that we don't define
        # Plus any names we reference that aren't local, global, or nonlocal
        scope.free_variables = child_free_vars - scope.local_names - scope.global_names

        return scope.free_variables

    def visit_Module(self, node: ast.Module) -> None:
        """Visit module - already handled in analyze()."""
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit a function definition - creates new scope."""
        # Function name is defined in enclosing scope
        self._add_local_name(node.name)

        # Create new scope for function body
        self._push_scope(ScopeType.FUNCTION, node.name, node)

        # Parameters are local to function
        for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
            self._add_local_name(arg.arg)
        if node.args.vararg:
            self._add_local_name(node.args.vararg.arg)
        if node.args.kwarg:
            self._add_local_name(node.args.kwarg.arg)

        self.generic_visit(node)
        self._pop_scope()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit an async function definition - creates new scope."""
        self._add_local_name(node.name)

        self._push_scope(ScopeType.ASYNC_FUNCTION, node.name, node)

        for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
            self._add_local_name(arg.arg)
        if node.args.vararg:
            self._add_local_name(node.args.vararg.arg)
        if node.args.kwarg:
            self._add_local_name(node.args.kwarg.arg)

        self.generic_visit(node)
        self._pop_scope()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit a class definition - creates new scope."""
        self._add_local_name(node.name)

        self._push_scope(ScopeType.CLASS, node.name, node)
        self.generic_visit(node)
        self._pop_scope()

    def visit_Lambda(self, node: ast.Lambda) -> None:
        """Visit a lambda - creates new scope."""
        self._push_scope(ScopeType.LAMBDA, "<lambda>", node)

        for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
            self._add_local_name(arg.arg)
        if node.args.vararg:
            self._add_local_name(node.args.vararg.arg)
        if node.args.kwarg:
            self._add_local_name(node.args.kwarg.arg)

        self.generic_visit(node)
        self._pop_scope()

    def visit_ListComp(self, node: ast.ListComp) -> None:
        """Visit list comprehension - creates new scope in Python 3."""
        self._push_scope(ScopeType.COMPREHENSION, "<listcomp>", node)
        self.generic_visit(node)
        self._pop_scope()

    def visit_SetComp(self, node: ast.SetComp) -> None:
        """Visit set comprehension."""
        self._push_scope(ScopeType.COMPREHENSION, "<setcomp>", node)
        self.generic_visit(node)
        self._pop_scope()

    def visit_DictComp(self, node: ast.DictComp) -> None:
        """Visit dict comprehension."""
        self._push_scope(ScopeType.COMPREHENSION, "<dictcomp>", node)
        self.generic_visit(node)
        self._pop_scope()

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        """Visit generator expression."""
        self._push_scope(ScopeType.COMPREHENSION, "<genexpr>", node)
        self.generic_visit(node)
        self._pop_scope()

    def visit_comprehension(self, node: ast.comprehension) -> None:
        """Visit comprehension target - adds loop variable."""
        if isinstance(node.target, ast.Name):
            self._add_local_name(node.target.id)
        elif isinstance(node.target, ast.Tuple):
            for elt in ast.walk(node.target):
                if isinstance(elt, ast.Name):
                    self._add_local_name(elt.id)
        self.generic_visit(node)

    def visit_Global(self, node: ast.Global) -> None:
        """Visit global declaration."""
        if self.current_scope:
            for name in node.names:
                self.current_scope.global_names.add(name)

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        """Visit nonlocal declaration."""
        if self.current_scope:
            for name in node.names:
                self.current_scope.nonlocal_names.add(name)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignment - adds targets as local names."""
        for target in node.targets:
            self._collect_assigned_names(target)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Visit annotated assignment."""
        self._collect_assigned_names(node.target)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        """Visit augmented assignment."""
        self._collect_assigned_names(node.target)
        self.generic_visit(node)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        """Visit walrus operator (:=)."""
        if isinstance(node.target, ast.Name):
            # Walrus operator binds in enclosing non-comprehension scope
            scope = self.current_scope
            while scope and scope.type == ScopeType.COMPREHENSION:
                scope = scope.parent
            if scope:
                scope.local_names.add(node.target.id)
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        """Visit for loop - adds target as local."""
        self._collect_assigned_names(node.target)
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        """Visit async for loop."""
        self._collect_assigned_names(node.target)
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        """Visit with statement."""
        for item in node.items:
            if item.optional_vars:
                self._collect_assigned_names(item.optional_vars)
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        """Visit async with statement."""
        for item in node.items:
            if item.optional_vars:
                self._collect_assigned_names(item.optional_vars)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        """Visit exception handler."""
        if node.name:
            self._add_local_name(node.name)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        """Visit import statement."""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name.split(".")[0]
            self._add_local_name(name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit from...import statement."""
        for alias in node.names:
            if alias.name == "*":
                # Can't determine names from star import statically
                continue
            name = alias.asname if alias.asname else alias.name
            self._add_local_name(name)

    def _collect_assigned_names(self, target: ast.AST) -> None:
        """Collect all names from an assignment target."""
        if isinstance(target, ast.Name):
            self._add_local_name(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._collect_assigned_names(elt)
        elif isinstance(target, ast.Starred):
            self._collect_assigned_names(target.value)


class NameResolver(ParentTrackingVisitor):
    """
    Visitor for resolving names to their definitions.

    Implements P1-AST-004: Name binding and reference resolution.
    """

    # Python built-in names
    BUILTINS = set(dir(__builtins__)) if isinstance(__builtins__, dict) else set(dir(__builtins__))

    def __init__(self, scope_tree: PythonScope, symbols: list[PythonSymbol]):
        super().__init__()
        self.scope_tree = scope_tree
        self.symbols = symbols
        self.symbol_by_qname: dict[str, PythonSymbol] = {s.qualified_name: s for s in symbols}
        self.references: list[NameReference] = []
        self.current_scope: PythonScope | None = None
        self.scope_for_node: dict[int, PythonScope] = {}

        # Build scope lookup
        self._build_scope_map(scope_tree)

    def _build_scope_map(self, scope: PythonScope) -> None:
        """Build mapping from AST nodes to scopes."""
        if scope.node:
            self.scope_for_node[id(scope.node)] = scope
        for child in scope.children:
            self._build_scope_map(child)

    def resolve(self, tree: ast.Module) -> list[NameReference]:
        """Resolve all name references."""
        self.current_scope = self.scope_tree
        self.visit(tree)
        return self.references

    def visit(self, node: ast.AST) -> Any:
        """Visit a node, updating current scope if needed."""
        node_id = id(node)
        if node_id in self.scope_for_node:
            old_scope = self.current_scope
            self.current_scope = self.scope_for_node[node_id]
            result = super().visit(node)
            self.current_scope = old_scope
            return result
        return super().visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        """Visit a name reference."""
        context = NameContext.LOAD
        if isinstance(node.ctx, ast.Store):
            context = NameContext.STORE
        elif isinstance(node.ctx, ast.Del):
            context = NameContext.DELETE

        definition = self._resolve_name(node.id, self.current_scope)
        is_undefined = definition is None and node.id not in self.BUILTINS
        is_builtin = node.id in self.BUILTINS and definition is None

        ref = NameReference(
            name=node.id,
            node=node,
            context=context,
            definition=definition,
            scope=self.current_scope,
            location=SourceLocation.from_node(node),
            is_undefined=is_undefined,
            is_builtin=is_builtin,
        )
        self.references.append(ref)

    def _resolve_name(self, name: str, scope: PythonScope | None) -> PythonSymbol | None:
        """
        Resolve a name using LEGB rule.

        L - Local (innermost scope)
        E - Enclosing (nonlocal) scopes
        G - Global (module level)
        B - Built-in (handled separately)
        """
        if scope is None:
            return None

        # Check if explicitly declared global
        if name in scope.global_names:
            # Jump to module scope
            return self._find_in_global_scope(name, scope)

        # Check if explicitly declared nonlocal
        if name in scope.nonlocal_names:
            # Search enclosing scopes (skip current)
            return self._find_in_enclosing_scope(name, scope.parent)

        # Local scope (for class scope, only applies in certain contexts)
        if scope.type != ScopeType.CLASS:
            if name in scope.local_names:
                return self._find_symbol_in_scope(name, scope)

        # Enclosing scopes (skip class scopes per Python semantics)
        enclosing = scope.parent
        while enclosing:
            if enclosing.type != ScopeType.CLASS and name in enclosing.local_names:
                return self._find_symbol_in_scope(name, enclosing)
            enclosing = enclosing.parent

        # Global scope
        return self._find_in_global_scope(name, scope)

    def _find_in_global_scope(self, name: str, scope: PythonScope) -> PythonSymbol | None:
        """Find a name in the global (module) scope."""
        # Navigate to root
        root = scope
        while root.parent:
            root = root.parent
        return self._find_symbol_in_scope(name, root)

    def _find_in_enclosing_scope(self, name: str, scope: PythonScope | None) -> PythonSymbol | None:
        """Find a name in enclosing scopes."""
        while scope:
            if scope.type != ScopeType.CLASS and name in scope.local_names:
                return self._find_symbol_in_scope(name, scope)
            scope = scope.parent
        return None

    def _find_symbol_in_scope(self, name: str, scope: PythonScope) -> PythonSymbol | None:
        """Find a symbol definition in a scope."""
        # Try to find in our symbol table
        scope_prefix = self._get_scope_prefix(scope)
        qualified_name = f"{scope_prefix}.{name}" if scope_prefix else name

        if qualified_name in self.symbol_by_qname:
            return self.symbol_by_qname[qualified_name]

        # Check for just the name (module-level)
        if name in self.symbol_by_qname:
            return self.symbol_by_qname[name]

        return None

    def _get_scope_prefix(self, scope: PythonScope) -> str:
        """Get the qualified name prefix for a scope."""
        parts = []
        current: PythonScope | None = scope
        while current and current.type != ScopeType.MODULE:
            if current.type not in (ScopeType.COMPREHENSION, ScopeType.LAMBDA):
                parts.append(current.name)
            current = current.parent
        return ".".join(reversed(parts))


# =============================================================================
# Call Graph Builder - P2-AST-005
# =============================================================================


class CallGraphBuilder(ParentTrackingVisitor):
    """
    Visitor for building call graphs from AST.

    Implements P2-AST-005: Call graph generation.
    """

    # Dynamic call functions that we flag
    DYNAMIC_CALL_FUNCS = {"getattr", "eval", "exec", "compile", "__import__"}

    def __init__(self, module: PythonModule):
        super().__init__()
        self.module = module
        self.call_graph = CallGraph()
        self.current_function: PythonFunction | None = None

        # Build function lookup by qualified name
        self.functions_by_qname: dict[str, PythonFunction] = {}
        self._build_function_lookup()

    def _build_function_lookup(self) -> None:
        """Build lookup table for functions."""
        for func in self.module.functions:
            self.functions_by_qname[func.qualified_name] = func
            self.functions_by_qname[func.name] = func  # Also by simple name
            self.call_graph.add_node(func)

        for cls in self.module.classes:
            for method in cls.methods:
                self.functions_by_qname[method.qualified_name] = method
                # Also register as ClassName.method for method resolution
                self.call_graph.add_node(method)

    def build(self, tree: ast.Module) -> CallGraph:
        """Build call graph from AST."""
        self.visit(tree)

        # Track which functions are called and which call others using id()
        called_func_ids: set[int] = set()
        caller_func_ids: set[int] = set()

        for edge in self.call_graph.edges:
            if edge.callee:
                called_func_ids.add(id(edge.callee))
            caller_func_ids.add(id(edge.caller))

        # Compute entry points (functions not called by anyone)
        for func in self.call_graph.nodes:
            if id(func) not in called_func_ids:
                self.call_graph.entry_points.append(func)

        # Compute leaf functions (functions that don't call anything)
        for func in self.call_graph.nodes:
            if id(func) not in caller_func_ids:
                self.call_graph.leaf_functions.append(func)

        # Detect recursive functions
        for func in self.call_graph.nodes:
            if self._is_recursive(func):
                self.call_graph.recursive_functions.append(func)

        return self.call_graph

    def _is_recursive(self, func: PythonFunction) -> bool:
        """Check if a function is recursive (directly or indirectly)."""
        func_id = id(func)

        # Direct recursion
        for edge in self.call_graph.edges:
            if id(edge.caller) == func_id and edge.callee and id(edge.callee) == func_id:
                return True

        # Indirect recursion (simple check: can we reach func from func?)
        visited_ids: set[int] = set()
        to_visit: list[PythonFunction] = [func]

        while to_visit:
            current = to_visit.pop()
            current_id = id(current)
            if current_id in visited_ids:
                continue
            visited_ids.add(current_id)

            for callee in self.call_graph.get_callees(current):
                if id(callee) == func_id:
                    return True
                if id(callee) not in visited_ids:
                    to_visit.append(callee)

        return False

    def _find_function_for_node(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> PythonFunction | None:
        """Find the PythonFunction object corresponding to an AST node."""
        for func in self.module.functions:
            if func.location.line == node.lineno and func.name == node.name:
                return func

        for cls in self.module.classes:
            for method in cls.methods:
                if method.location.line == node.lineno and method.name == node.name:
                    return method

        return None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition - track as current caller."""
        # Find the PythonFunction for this node
        func = self._find_function_for_node(node)
        if func:
            old_func = self.current_function
            self.current_function = func
            self.generic_visit(node)
            self.current_function = old_func
        else:
            self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definition."""
        func = self._find_function_for_node(node)
        if func:
            old_func = self.current_function
            self.current_function = func
            self.generic_visit(node)
            self.current_function = old_func
        else:
            self.generic_visit(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        """Visit lambda - lambdas don't create new call context for our purposes."""
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Visit a function call."""
        if self.current_function is None:
            # Module-level call, skip for now
            self.generic_visit(node)
            return

        # Extract call information
        callee_name, receiver, is_dynamic = self._extract_call_info(node)

        # Try to resolve the callee
        callee = self._resolve_callee(callee_name, receiver)

        # Count arguments
        args_count = len(node.args)
        has_starargs = any(isinstance(arg, ast.Starred) for arg in node.args)
        has_kwargs = bool(node.keywords) or any(kw.arg is None for kw in node.keywords) if node.keywords else False

        # Create call site
        call_site = CallSite(
            caller=self.current_function,
            callee_name=callee_name,
            callee=callee,
            receiver=receiver,
            args_count=args_count,
            has_starargs=has_starargs,
            has_kwargs=has_kwargs,
            is_dynamic=is_dynamic,
            location=SourceLocation.from_node(node),
        )

        self.call_graph.edges.append(call_site)

        # Continue visiting to handle nested calls
        self.generic_visit(node)

    def _extract_call_info(self, node: ast.Call) -> tuple[str, str | None, bool]:
        """
        Extract call information from a Call node.

        Returns:
            (callee_name, receiver, is_dynamic)
        """
        func = node.func

        # Simple name call: foo()
        if isinstance(func, ast.Name):
            is_dynamic = func.id in self.DYNAMIC_CALL_FUNCS
            return func.id, None, is_dynamic

        # Attribute call: obj.method() or module.func()
        if isinstance(func, ast.Attribute):
            method_name = func.attr

            # Extract receiver
            if isinstance(func.value, ast.Name):
                receiver = func.value.id
            elif isinstance(func.value, ast.Attribute):
                receiver = ast.unparse(func.value)
            elif isinstance(func.value, ast.Call):
                # Chained call: foo().bar()
                receiver = "<call>"
            else:
                receiver = ast.unparse(func.value) if hasattr(ast, "unparse") else "<expr>"

            return method_name, receiver, False

        # Subscript call: foo[bar]()
        if isinstance(func, ast.Subscript):
            return "<subscript>", None, True

        # Other complex expressions
        return "<dynamic>", None, True

    def _resolve_callee(self, name: str, receiver: str | None) -> PythonFunction | None:
        """Try to resolve a callee name to a PythonFunction."""
        if receiver:
            # Try ClassName.method format
            qualified = f"{receiver}.{name}"
            if qualified in self.functions_by_qname:
                return self.functions_by_qname[qualified]

            # Check if receiver might be 'self' and we're in a class
            if receiver == "self" and self.current_function:
                # Find the class this method belongs to
                parent = self.current_function.parent
                if parent and isinstance(parent, PythonClass):
                    qualified = f"{parent.name}.{name}"
                    if qualified in self.functions_by_qname:
                        return self.functions_by_qname[qualified]

        # Try simple name lookup
        if name in self.functions_by_qname:
            return self.functions_by_qname[name]

        return None


# =============================================================================
# Control Flow Graph Builder - P2-AST-006
# =============================================================================


class CFGBuilder(ast.NodeVisitor):
    """
    Builder for Control Flow Graphs from Python AST.

    Implements P2-AST-006: CFG generation.

    A CFG represents the flow of control through a function:
    - Basic blocks contain sequential statements
    - Edges represent possible control flow between blocks
    - Entry and exit blocks are marked
    - Exception handlers are tracked

    Handles:
    - Sequential statements
    - If/elif/else branches
    - While and for loops (with break/continue)
    - Try/except/finally blocks
    - With statements
    - Match statements (Python 3.10+)
    - Return, raise, and assert statements
    """

    def __init__(self, function: PythonFunction):
        self.function = function
        self.blocks: list[BasicBlock] = []
        self.current_block: BasicBlock | None = None
        self.block_counter = 0

        # Entry and exit blocks
        self.entry_block: BasicBlock | None = None
        self.exit_block: BasicBlock | None = None

        # Track loop contexts for break/continue
        self.loop_stack: list[tuple[BasicBlock, BasicBlock]] = []  # (loop_entry, loop_exit)

        # Track finally blocks for proper control flow
        self.finally_stack: list[BasicBlock] = []

    def _new_block(
        self,
        label: str = "",
        is_entry: bool = False,
        is_exit: bool = False,
        is_exception_handler: bool = False,
        exception_type: str | None = None,
    ) -> BasicBlock:
        """Create a new basic block."""
        block = BasicBlock(
            id=self.block_counter,
            label=label,
            is_entry=is_entry,
            is_exit=is_exit,
            is_exception_handler=is_exception_handler,
            exception_type=exception_type,
        )
        self.block_counter += 1
        self.blocks.append(block)
        return block

    def _add_edge(self, from_block: BasicBlock | None, to_block: BasicBlock | None) -> None:
        """Add an edge between two blocks."""
        if from_block is None or to_block is None:
            return
        if to_block not in from_block.successors:
            from_block.successors.append(to_block)
        if from_block not in to_block.predecessors:
            to_block.predecessors.append(from_block)

    def _set_current_block(self, block: BasicBlock) -> None:
        """Set the current block for adding statements."""
        self.current_block = block

    def build(self, func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> ControlFlowGraph:
        """Build CFG from a function definition AST node."""
        # Create entry and exit blocks
        self.entry_block = self._new_block("entry", is_entry=True)
        self.exit_block = self._new_block("exit", is_exit=True)

        # Start building from entry
        self._set_current_block(self.entry_block)

        # Process function body
        for stmt in func_node.body:
            self._visit_stmt(stmt)

        # If we didn't return, fall through to exit
        if self.current_block and not self._is_terminal_block(self.current_block):
            self._add_edge(self.current_block, self.exit_block)

        return ControlFlowGraph(
            function=self.function,
            entry_block=self.entry_block,
            exit_block=self.exit_block,
            blocks=self.blocks,
        )

    def _is_terminal_block(self, block: BasicBlock) -> bool:
        """Check if block already has a terminal statement (return/raise)."""
        if not block.statements:
            return False
        last_stmt = block.statements[-1]
        return isinstance(last_stmt, (ast.Return, ast.Raise))

    def _visit_stmt(self, stmt: ast.stmt) -> None:
        """Visit a statement and update CFG."""
        if self.current_block is None:
            # Dead code - create unreachable block
            self.current_block = self._new_block("unreachable")

        # Dispatch based on statement type
        if isinstance(stmt, ast.If):
            self._visit_if(stmt)
        elif isinstance(stmt, ast.While):
            self._visit_while(stmt)
        elif isinstance(stmt, ast.For):
            self._visit_for(stmt)
        elif isinstance(stmt, ast.Try):
            self._visit_try(stmt)
        elif isinstance(stmt, ast.With):
            self._visit_with(stmt)
        elif isinstance(stmt, ast.AsyncWith):
            self._visit_with(stmt)
        elif isinstance(stmt, ast.Match):
            self._visit_match(stmt)
        elif isinstance(stmt, ast.Return):
            self._visit_return(stmt)
        elif isinstance(stmt, ast.Raise):
            self._visit_raise(stmt)
        elif isinstance(stmt, ast.Break):
            self._visit_break(stmt)
        elif isinstance(stmt, ast.Continue):
            self._visit_continue(stmt)
        elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            # Nested definitions - add to current block but don't change flow
            if self.current_block is not None:
                self.current_block.statements.append(stmt)
        else:
            # Simple statements: Expr, Assign, AugAssign, AnnAssign,
            # Delete, Pass, Import, ImportFrom, Global, Nonlocal, Assert
            if self.current_block is not None:
                self.current_block.statements.append(stmt)

    def _visit_if(self, stmt: ast.If) -> None:
        """Handle if/elif/else statements."""
        # Add condition test to current block
        if self.current_block is not None:
            self.current_block.statements.append(stmt)

        # Create blocks for branches
        then_block = self._new_block("if_then")

        # After block for merging
        after_block = self._new_block("if_after")

        # Connect test to then-block
        self._add_edge(self.current_block, then_block)

        # Process then-block
        self._set_current_block(then_block)
        for s in stmt.body:
            self._visit_stmt(s)

        # Connect end of then to after (if not terminal)
        if self.current_block and not self._is_terminal_block(self.current_block):
            self._add_edge(self.current_block, after_block)

        # Process else/elif
        if stmt.orelse:
            else_block = self._new_block("if_else")
            self._add_edge(self.blocks[self.block_counter - 3], else_block)  # From test block

            self._set_current_block(else_block)
            for s in stmt.orelse:
                self._visit_stmt(s)

            if self.current_block and not self._is_terminal_block(self.current_block):
                self._add_edge(self.current_block, after_block)
        else:
            # No else: connect test directly to after
            self._add_edge(self.blocks[self.block_counter - 2], after_block)  # From test block

        self._set_current_block(after_block)

    def _visit_while(self, stmt: ast.While) -> None:
        """Handle while loops."""
        # Create loop header block
        loop_header = self._new_block("while_header")
        loop_body = self._new_block("while_body")
        loop_after = self._new_block("while_after")

        # Connect current to header
        self._add_edge(self.current_block, loop_header)

        # Header has the test
        loop_header.statements.append(stmt)

        # Connect header to body (True) and after (False)
        self._add_edge(loop_header, loop_body)
        self._add_edge(loop_header, loop_after)

        # Push loop context
        self.loop_stack.append((loop_header, loop_after))

        # Process body
        self._set_current_block(loop_body)
        for s in stmt.body:
            self._visit_stmt(s)

        # Connect end of body back to header
        if self.current_block and not self._is_terminal_block(self.current_block):
            self._add_edge(self.current_block, loop_header)

        # Pop loop context
        self.loop_stack.pop()

        # Handle else clause (runs when loop completes normally)
        if stmt.orelse:
            else_block = self._new_block("while_else")
            self._add_edge(loop_header, else_block)

            self._set_current_block(else_block)
            for s in stmt.orelse:
                self._visit_stmt(s)

            if self.current_block and not self._is_terminal_block(self.current_block):
                self._add_edge(self.current_block, loop_after)

        self._set_current_block(loop_after)

    def _visit_for(self, stmt: ast.For) -> None:
        """Handle for loops."""
        # Similar to while but with iterator
        loop_header = self._new_block("for_header")
        loop_body = self._new_block("for_body")
        loop_after = self._new_block("for_after")

        # Connect current to header
        self._add_edge(self.current_block, loop_header)

        # Header has the iteration
        loop_header.statements.append(stmt)

        # Connect header to body (has items) and after (exhausted)
        self._add_edge(loop_header, loop_body)
        self._add_edge(loop_header, loop_after)

        # Push loop context
        self.loop_stack.append((loop_header, loop_after))

        # Process body
        self._set_current_block(loop_body)
        for s in stmt.body:
            self._visit_stmt(s)

        # Connect end of body back to header
        if self.current_block and not self._is_terminal_block(self.current_block):
            self._add_edge(self.current_block, loop_header)

        # Pop loop context
        self.loop_stack.pop()

        # Handle else clause
        if stmt.orelse:
            else_block = self._new_block("for_else")
            self._add_edge(loop_header, else_block)

            self._set_current_block(else_block)
            for s in stmt.orelse:
                self._visit_stmt(s)

            if self.current_block and not self._is_terminal_block(self.current_block):
                self._add_edge(self.current_block, loop_after)

        self._set_current_block(loop_after)

    def _visit_try(self, stmt: ast.Try) -> None:
        """Handle try/except/else/finally blocks."""
        try_block = self._new_block("try_body")
        after_block = self._new_block("try_after")

        # Connect current to try
        self._add_edge(self.current_block, try_block)

        # Track finally if present
        finally_block: BasicBlock | None = None
        if stmt.finalbody:
            finally_block = self._new_block("try_finally")
            self.finally_stack.append(finally_block)

        # Process try body
        self._set_current_block(try_block)
        for s in stmt.body:
            self._visit_stmt(s)

        try_end = self.current_block

        # Create exception handlers
        except_blocks: list[BasicBlock] = []
        for handler in stmt.handlers:
            exc_type = handler.type
            type_name = (
                ast.unparse(exc_type)
                if exc_type and hasattr(ast, "unparse")
                else ((exc_type.id if isinstance(exc_type, ast.Name) else "Exception") if exc_type else "BaseException")
            )

            handler_block = self._new_block(
                f"except_{type_name}",
                is_exception_handler=True,
                exception_type=type_name,
            )
            except_blocks.append(handler_block)

            # Try body can jump to any exception handler
            self._add_edge(try_block, handler_block)

            # Process handler body
            self._set_current_block(handler_block)
            for s in handler.body:
                self._visit_stmt(s)

            # Handler flows to finally or after
            if self.current_block and not self._is_terminal_block(self.current_block):
                if finally_block:
                    self._add_edge(self.current_block, finally_block)
                else:
                    self._add_edge(self.current_block, after_block)

        # Handle else clause (runs if no exception)
        if stmt.orelse:
            else_block = self._new_block("try_else")
            if try_end and not self._is_terminal_block(try_end):
                self._add_edge(try_end, else_block)

            self._set_current_block(else_block)
            for s in stmt.orelse:
                self._visit_stmt(s)

            if self.current_block and not self._is_terminal_block(self.current_block):
                if finally_block:
                    self._add_edge(self.current_block, finally_block)
                else:
                    self._add_edge(self.current_block, after_block)
        else:
            # No else: try body flows to finally or after
            if try_end and not self._is_terminal_block(try_end):
                if finally_block:
                    self._add_edge(try_end, finally_block)
                else:
                    self._add_edge(try_end, after_block)

        # Handle finally
        if finally_block:
            self.finally_stack.pop()

            self._set_current_block(finally_block)
            for s in stmt.finalbody:
                self._visit_stmt(s)

            if self.current_block and not self._is_terminal_block(self.current_block):
                self._add_edge(self.current_block, after_block)

        self._set_current_block(after_block)

    def _visit_with(self, stmt: ast.With | ast.AsyncWith) -> None:
        """Handle with/async with statements."""
        # With is similar to try/finally but simpler
        with_block = self._new_block("with_body")
        after_block = self._new_block("with_after")

        # Add context manager setup to current block
        if self.current_block is not None:
            self.current_block.statements.append(stmt)

        # Connect to with body
        self._add_edge(self.current_block, with_block)

        # Process body
        self._set_current_block(with_block)
        for s in stmt.body:
            self._visit_stmt(s)

        # Connect to after (context manager cleanup)
        if self.current_block and not self._is_terminal_block(self.current_block):
            self._add_edge(self.current_block, after_block)

        self._set_current_block(after_block)

    def _visit_match(self, stmt: ast.Match) -> None:
        """Handle match statements (Python 3.10+)."""
        # Match is like a series of if/elif
        match_block = self.current_block
        if match_block is not None:
            match_block.statements.append(stmt)

        after_block = self._new_block("match_after")

        for case in stmt.cases:
            case_block = self._new_block("match_case")
            self._add_edge(match_block, case_block)

            self._set_current_block(case_block)
            for s in case.body:
                self._visit_stmt(s)

            if self.current_block and not self._is_terminal_block(self.current_block):
                self._add_edge(self.current_block, after_block)

        self._set_current_block(after_block)

    def _visit_return(self, stmt: ast.Return) -> None:
        """Handle return statements."""
        if self.current_block is not None:
            self.current_block.statements.append(stmt)

        # Return goes to finally blocks then exit
        if self.finally_stack:
            # Need to go through finally blocks
            for finally_block in reversed(self.finally_stack):
                self._add_edge(self.current_block, finally_block)
        else:
            self._add_edge(self.current_block, self.exit_block)

        # Mark that control doesn't continue after return
        self.current_block = None

    def _visit_raise(self, stmt: ast.Raise) -> None:
        """Handle raise statements."""
        if self.current_block is not None:
            self.current_block.statements.append(stmt)

        # Raise can go to exception handlers or finally
        if self.finally_stack:
            for finally_block in reversed(self.finally_stack):
                self._add_edge(self.current_block, finally_block)

        # Also add edge to exit (unhandled exception)
        self._add_edge(self.current_block, self.exit_block)

        self.current_block = None

    def _visit_break(self, stmt: ast.Break) -> None:
        """Handle break statements."""
        if self.current_block is not None:
            self.current_block.statements.append(stmt)

        if self.loop_stack:
            _, loop_exit = self.loop_stack[-1]
            self._add_edge(self.current_block, loop_exit)

        self.current_block = None

    def _visit_continue(self, stmt: ast.Continue) -> None:
        """Handle continue statements."""
        if self.current_block is not None:
            self.current_block.statements.append(stmt)

        if self.loop_stack:
            loop_header, _ = self.loop_stack[-1]
            self._add_edge(self.current_block, loop_header)

        self.current_block = None


# =============================================================================
# Data Flow Analyzer - P2-AST-007
# =============================================================================


class DataFlowAnalyzer:
    """
    Data flow analyzer for control flow graphs.

    Implements P2-AST-007: Data flow analysis.

    Computes:
    - Reaching definitions: which definitions can reach each block
    - Live variables: which variables are live at each block
    - Def-use chains: which uses depend on which definitions
    - Use-def chains: which definitions can reach each use
    - Dead assignments: definitions that are never used
    - Undefined uses: uses that have no reaching definition
    """

    def __init__(self, cfg: ControlFlowGraph, function: PythonFunction):
        self.cfg = cfg
        self.function = function

        # Block-level info
        self.block_gen: dict[int, set[Definition]] = {}  # Definitions generated in block
        self.block_kill: dict[int, set[Definition]] = {}  # Definitions killed in block
        self.block_use: dict[int, set[str]] = {}  # Variables used in block
        self.block_def: dict[int, set[str]] = {}  # Variables defined in block

        # All definitions by variable name
        self.all_definitions: list[Definition] = []
        self.definitions_by_var: dict[str, list[Definition]] = {}

        # Results
        self.reaching_definitions: dict[int, set[Definition]] = {}
        self.live_variables: dict[int, set[str]] = {}

    def analyze(self) -> DataFlowInfo:
        """Perform data flow analysis and return results."""
        # Phase 1: Collect definitions and uses from each block
        self._collect_block_info()

        # Phase 2: Compute reaching definitions
        self._compute_reaching_definitions()

        # Phase 3: Compute live variables
        self._compute_live_variables()

        # Phase 4: Build def-use and use-def chains
        def_use_chains, use_def_chains = self._build_chains()

        # Phase 5: Find dead assignments and undefined uses
        dead_assignments = self._find_dead_assignments(def_use_chains)
        undefined_uses = self._find_undefined_uses()

        # Phase 6: Optimization analyses
        constant_values = self._compute_constant_propagation()
        available_expressions = self._compute_available_expressions()
        very_busy_expressions = self._compute_very_busy_expressions()

        # Convert block id keys to BasicBlock objects for the result
        reaching_defs_by_block = {self._get_block(bid): defs for bid, defs in self.reaching_definitions.items()}
        live_vars_by_block = {self._get_block(bid): vars for bid, vars in self.live_variables.items()}
        constants_by_block = {self._get_block(bid): vals for bid, vals in constant_values.items()}
        available_by_block = {self._get_block(bid): exprs for bid, exprs in available_expressions.items()}
        very_busy_by_block = {self._get_block(bid): exprs for bid, exprs in very_busy_expressions.items()}

        return DataFlowInfo(
            reaching_definitions=reaching_defs_by_block,
            live_variables=live_vars_by_block,
            def_use_chains=def_use_chains,
            use_def_chains=use_def_chains,
            dead_assignments=dead_assignments,
            undefined_uses=undefined_uses,
            constant_values=constants_by_block,
            available_expressions=available_by_block,
            very_busy_expressions=very_busy_by_block,
        )

    def _get_block(self, block_id: int) -> BasicBlock:
        """Get block by id."""
        for block in self.cfg.blocks:
            if block.id == block_id:
                return block
        raise ValueError(f"Block {block_id} not found")

    def _collect_block_info(self) -> None:
        """Collect definitions and uses from each block."""
        # Add parameter definitions from entry block
        if self.cfg.entry_block:
            entry_id = self.cfg.entry_block.id
            self.block_gen[entry_id] = set()
            self.block_kill[entry_id] = set()
            self.block_use[entry_id] = set()
            self.block_def[entry_id] = set()

            for param in self.function.parameters:
                defn = Definition(
                    variable=param.name,
                    node=None,  # No AST node for parameters
                    block=self.cfg.entry_block,
                    is_parameter=True,
                )
                self.all_definitions.append(defn)
                self.definitions_by_var.setdefault(param.name, []).append(defn)
                self.block_gen[entry_id].add(defn)
                self.block_def[entry_id].add(param.name)

        # Process each block
        for block in self.cfg.blocks:
            if block.id not in self.block_gen:
                self.block_gen[block.id] = set()
                self.block_kill[block.id] = set()
                self.block_use[block.id] = set()
                self.block_def[block.id] = set()

            for stmt in block.statements:
                self._process_statement(stmt, block)

    def _process_statement(self, stmt: ast.stmt, block: BasicBlock) -> None:
        """Process a statement for definitions and uses."""
        # First collect uses (before any definitions in this statement)
        for node in ast.walk(stmt):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                if node.id not in self.block_def[block.id]:
                    self.block_use[block.id].add(node.id)

        # Then collect definitions
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                self._collect_assignments(target, stmt, block)
        elif isinstance(stmt, ast.AnnAssign) and stmt.value:
            self._collect_assignments(stmt.target, stmt, block)
        elif isinstance(stmt, ast.AugAssign):
            # x += y means use of x then def of x
            if isinstance(stmt.target, ast.Name):
                name = stmt.target.id
                if name not in self.block_def[block.id]:
                    self.block_use[block.id].add(name)
                self._add_definition(name, stmt, block)
        elif isinstance(stmt, (ast.For, ast.AsyncFor)):
            # Loop variable is a definition
            self._collect_assignments(stmt.target, stmt, block)
        elif isinstance(stmt, (ast.With, ast.AsyncWith)):
            for item in stmt.items:
                if item.optional_vars:
                    self._collect_assignments(item.optional_vars, stmt, block)
        elif isinstance(stmt, ast.ExceptHandler) and stmt.name:
            self._add_definition(stmt.name, stmt, block)
        elif isinstance(stmt, ast.NamedExpr):
            # Walrus operator: (x := value)
            if isinstance(stmt.target, ast.Name):
                self._add_definition(stmt.target.id, stmt, block)
        elif isinstance(stmt, ast.Global):
            for name in stmt.names:
                defn = Definition(
                    variable=name,
                    node=stmt,
                    block=block,
                    is_global=True,
                )
                self.all_definitions.append(defn)
                self.definitions_by_var.setdefault(name, []).append(defn)
        elif isinstance(stmt, ast.Nonlocal):
            for name in stmt.names:
                defn = Definition(
                    variable=name,
                    node=stmt,
                    block=block,
                    is_nonlocal=True,
                )
                self.all_definitions.append(defn)
                self.definitions_by_var.setdefault(name, []).append(defn)

    def _collect_assignments(self, target: ast.AST, stmt: ast.stmt, block: BasicBlock) -> None:
        """Collect assignments from a target (handles unpacking)."""
        if isinstance(target, ast.Name):
            self._add_definition(target.id, stmt, block)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._collect_assignments(elt, stmt, block)
        elif isinstance(target, ast.Starred):
            self._collect_assignments(target.value, stmt, block)
        # Skip Subscript and Attribute - not simple variable assignments

    def _add_definition(self, name: str, node: ast.AST, block: BasicBlock) -> None:
        """Add a definition to tracking structures."""
        defn = Definition(
            variable=name,
            node=node,
            block=block,
        )
        self.all_definitions.append(defn)
        self.definitions_by_var.setdefault(name, []).append(defn)
        self.block_gen[block.id].add(defn)
        self.block_def[block.id].add(name)

        # This definition kills all other definitions of the same variable
        for prev_defn in self.definitions_by_var.get(name, []):
            if prev_defn is not defn:
                self.block_kill[block.id].add(prev_defn)

    def _compute_reaching_definitions(self) -> None:
        """Compute reaching definitions for each block using iterative algorithm."""
        # Initialize
        for block in self.cfg.blocks:
            self.reaching_definitions[block.id] = set()

        # Iterate until fixed point
        changed = True
        while changed:
            changed = False

            for block in self.cfg.blocks:
                # IN[B] = ∪ OUT[P] for all predecessors P
                in_set: set[Definition] = set()
                for pred in block.predecessors:
                    out_set = (
                        self.reaching_definitions[pred.id] - self.block_kill.get(pred.id, set())
                    ) | self.block_gen.get(pred.id, set())
                    in_set |= out_set

                # For entry block, add parameter definitions
                if block.is_entry and self.block_gen.get(block.id):
                    in_set |= self.block_gen[block.id]

                if in_set != self.reaching_definitions[block.id]:
                    self.reaching_definitions[block.id] = in_set
                    changed = True

    def _compute_live_variables(self) -> None:
        """Compute live variables for each block using backward analysis."""
        # Initialize
        for block in self.cfg.blocks:
            self.live_variables[block.id] = set()

        # Iterate until fixed point (backward analysis)
        changed = True
        while changed:
            changed = False

            for block in self.cfg.blocks:
                # OUT[B] = ∪ IN[S] for all successors S
                out_set: set[str] = set()
                for succ in block.successors:
                    # IN[S] = USE[S] ∪ (OUT[S] - DEF[S])
                    succ_in = self.block_use.get(succ.id, set()) | (
                        self.live_variables.get(succ.id, set()) - self.block_def.get(succ.id, set())
                    )
                    out_set |= succ_in

                # LIVE[B] = USE[B] ∪ (OUT[B] - DEF[B])
                new_live = self.block_use.get(block.id, set()) | (out_set - self.block_def.get(block.id, set()))

                if new_live != self.live_variables[block.id]:
                    self.live_variables[block.id] = new_live
                    changed = True

    def _build_chains(
        self,
    ) -> tuple[dict[Definition, set[ast.Name]], dict[int, set[Definition]]]:
        """Build def-use and use-def chains."""
        def_use_chains: dict[Definition, set[ast.Name]] = {}
        use_def_chains: dict[int, set[Definition]] = {}

        for defn in self.all_definitions:
            def_use_chains[defn] = set()

        # For each block, match uses to reaching definitions
        for block in self.cfg.blocks:
            reaching = self.reaching_definitions[block.id]

            for stmt in block.statements:
                for node in ast.walk(stmt):
                    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                        name = node.id
                        node_id = id(node)
                        use_def_chains[node_id] = set()

                        # Find definitions of this variable that reach here
                        for defn in reaching:
                            if defn.variable == name:
                                def_use_chains[defn].add(node)
                                use_def_chains[node_id].add(defn)

        return def_use_chains, use_def_chains

    def _find_dead_assignments(self, def_use_chains: dict[Definition, set[ast.Name]]) -> list[Definition]:
        """Find definitions that are never used."""
        dead = []
        for defn, uses in def_use_chains.items():
            if not uses and not defn.is_parameter and not defn.is_global and not defn.is_nonlocal:
                dead.append(defn)
        return dead

    def _find_undefined_uses(self) -> list[ast.Name]:
        """Find uses that have no reaching definition."""
        undefined = []

        for block in self.cfg.blocks:
            # Get variables that are used but not defined before use
            local_defs: set[str] = set()

            for stmt in block.statements:
                for node in ast.walk(stmt):
                    if isinstance(node, ast.Name):
                        if isinstance(node.ctx, ast.Load):
                            name = node.id
                            # Check if defined locally before this use
                            if name not in local_defs:
                                # Check if any reaching definition exists
                                reaching = self.reaching_definitions[block.id]
                                if not any(d.variable == name for d in reaching):
                                    # Check builtins
                                    if name not in dir(__builtins__):
                                        undefined.append(node)
                        elif isinstance(node.ctx, ast.Store):
                            local_defs.add(node.id)

        return undefined

    def _compute_constant_propagation(self) -> dict[int, dict[str, ConstantValue]]:
        """
        Compute constant propagation using a forward data flow analysis.

        For each block, determines which variables have constant values.
        Uses a lattice: UNDEF < constants < NAC (Not A Constant)
        """
        # Initialize all variables to UNDEF
        all_vars: set[str] = set()
        for defn in self.all_definitions:
            all_vars.add(defn.variable)

        constant_in: dict[int, dict[str, ConstantValue]] = {}
        constant_out: dict[int, dict[str, ConstantValue]] = {}

        for block in self.cfg.blocks:
            constant_in[block.id] = {v: ConstantValue.undefined() for v in all_vars}
            constant_out[block.id] = {v: ConstantValue.undefined() for v in all_vars}

        # Parameters are not constant (could be any value)
        if self.cfg.entry_block:
            for param in self.function.parameters:
                constant_in[self.cfg.entry_block.id][param.name] = ConstantValue.not_constant()

        # Iterate until fixed point
        changed = True
        while changed:
            changed = False

            for block in self.cfg.blocks:
                # Meet of all predecessors
                if block.predecessors:
                    new_in: dict[str, ConstantValue] = {v: ConstantValue.undefined() for v in all_vars}
                    for pred in block.predecessors:
                        for var in all_vars:
                            new_in[var] = new_in[var].meet(constant_out[pred.id][var])
                    if new_in != constant_in[block.id]:
                        constant_in[block.id] = new_in
                        changed = True

                # Transfer function: process statements
                current = dict(constant_in[block.id])
                for stmt in block.statements:
                    self._process_stmt_for_constants(stmt, current)

                if current != constant_out[block.id]:
                    constant_out[block.id] = current
                    changed = True

        return constant_out

    def _process_stmt_for_constants(
        self,
        stmt: ast.stmt,
        constants: dict[str, ConstantValue],
    ) -> None:
        """Process a statement for constant propagation."""
        if isinstance(stmt, ast.Assign):
            value = self._evaluate_constant(stmt.value, constants)
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    constants[target.id] = value
        elif isinstance(stmt, ast.AnnAssign) and stmt.value:
            value = self._evaluate_constant(stmt.value, constants)
            if isinstance(stmt.target, ast.Name):
                constants[stmt.target.id] = value
        elif isinstance(stmt, ast.AugAssign):
            # Augmented assignments are generally not constant
            if isinstance(stmt.target, ast.Name):
                constants[stmt.target.id] = ConstantValue.not_constant()

    def _evaluate_constant(
        self,
        node: ast.expr,
        constants: dict[str, ConstantValue],
    ) -> ConstantValue:
        """Evaluate an expression to a constant if possible."""
        if isinstance(node, ast.Constant):
            return ConstantValue.constant(node.value)

        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            return constants.get(node.id, ConstantValue.not_constant())

        if isinstance(node, ast.UnaryOp):
            operand = self._evaluate_constant(node.operand, constants)
            if operand.is_constant:
                try:
                    if isinstance(node.op, ast.UAdd):
                        return ConstantValue.constant(+operand.value)  # type: ignore
                    if isinstance(node.op, ast.USub):
                        return ConstantValue.constant(-operand.value)  # type: ignore
                    if isinstance(node.op, ast.Not):
                        return ConstantValue.constant(not operand.value)
                    if isinstance(node.op, ast.Invert):
                        return ConstantValue.constant(~operand.value)  # type: ignore
                except Exception:
                    pass
            return ConstantValue.not_constant()

        if isinstance(node, ast.BinOp):
            left = self._evaluate_constant(node.left, constants)
            right = self._evaluate_constant(node.right, constants)
            if left.is_constant and right.is_constant:
                try:
                    result = self._eval_binop(node.op, left.value, right.value)
                    if result is not None:
                        return ConstantValue.constant(result)
                except Exception:
                    pass
            return ConstantValue.not_constant()

        if isinstance(node, ast.Compare):
            # Only handle simple comparisons
            if len(node.ops) == 1 and len(node.comparators) == 1:
                left = self._evaluate_constant(node.left, constants)
                right = self._evaluate_constant(node.comparators[0], constants)
                if left.is_constant and right.is_constant:
                    try:
                        result = self._eval_compare(node.ops[0], left.value, right.value)
                        if result is not None:
                            return ConstantValue.constant(result)
                    except Exception:
                        pass
            return ConstantValue.not_constant()

        # Other expressions are not constant
        return ConstantValue.not_constant()

    def _eval_binop(self, op: ast.operator, left: object, right: object) -> object | None:
        """Evaluate a binary operation on constants."""
        if isinstance(op, ast.Add):
            return left + right  # type: ignore
        if isinstance(op, ast.Sub):
            return left - right  # type: ignore
        if isinstance(op, ast.Mult):
            return left * right  # type: ignore
        if isinstance(op, ast.Div):
            return left / right  # type: ignore
        if isinstance(op, ast.FloorDiv):
            return left // right  # type: ignore
        if isinstance(op, ast.Mod):
            return left % right  # type: ignore
        if isinstance(op, ast.Pow):
            return left**right  # type: ignore
        if isinstance(op, ast.LShift):
            return left << right  # type: ignore
        if isinstance(op, ast.RShift):
            return left >> right  # type: ignore
        if isinstance(op, ast.BitOr):
            return left | right  # type: ignore
        if isinstance(op, ast.BitXor):
            return left ^ right  # type: ignore
        if isinstance(op, ast.BitAnd):
            return left & right  # type: ignore
        return None

    def _eval_compare(self, op: ast.cmpop, left: object, right: object) -> bool | None:
        """Evaluate a comparison on constants."""
        if isinstance(op, ast.Eq):
            return left == right
        if isinstance(op, ast.NotEq):
            return left != right
        if isinstance(op, ast.Lt):
            return left < right  # type: ignore
        if isinstance(op, ast.LtE):
            return left <= right  # type: ignore
        if isinstance(op, ast.Gt):
            return left > right  # type: ignore
        if isinstance(op, ast.GtE):
            return left >= right  # type: ignore
        if isinstance(op, ast.Is):
            return left is right
        if isinstance(op, ast.IsNot):
            return left is not right
        return None

    def _compute_available_expressions(self) -> dict[int, set[Expression]]:
        """
        Compute available expressions using forward data flow analysis.

        An expression is available at a point if it has been computed on
        all paths to that point and not killed (by redefining a variable).
        """
        # Collect all expressions
        all_expressions: set[Expression] = set()
        block_gen: dict[int, set[Expression]] = {}
        block_kill: dict[int, set[Expression]] = {}

        for block in self.cfg.blocks:
            gen: set[Expression] = set()
            kill: set[Expression] = set()

            for stmt in block.statements:
                # Find expressions generated
                for node in ast.walk(stmt):
                    if isinstance(node, ast.BinOp | ast.Compare | ast.UnaryOp):
                        expr = Expression.from_node(node)
                        all_expressions.add(expr)
                        # Only add to gen if not killed in this block yet
                        if not any(expr.is_killed_by(v) for v in self.block_def.get(block.id, set())):
                            gen.add(expr)

                # Find expressions killed by definitions in this statement
                defined_vars = self._get_defined_vars(stmt)
                for var in defined_vars:
                    for expr in all_expressions:
                        if expr.is_killed_by(var):
                            kill.add(expr)
                            gen.discard(expr)

            block_gen[block.id] = gen
            block_kill[block.id] = kill

        # Initialize
        avail_in: dict[int, set[Expression]] = {}
        avail_out: dict[int, set[Expression]] = {}

        for block in self.cfg.blocks:
            avail_in[block.id] = set() if block.is_entry else set(all_expressions)
            avail_out[block.id] = set()

        # Iterate until fixed point
        changed = True
        while changed:
            changed = False

            for block in self.cfg.blocks:
                # Intersection of all predecessors
                if block.predecessors:
                    new_in = set(all_expressions)
                    for pred in block.predecessors:
                        new_in &= avail_out[pred.id]
                    if new_in != avail_in[block.id]:
                        avail_in[block.id] = new_in
                        changed = True

                # Transfer: out = gen ∪ (in - kill)
                new_out = block_gen[block.id] | (avail_in[block.id] - block_kill[block.id])
                if new_out != avail_out[block.id]:
                    avail_out[block.id] = new_out
                    changed = True

        return avail_in

    def _compute_very_busy_expressions(self) -> dict[int, set[Expression]]:
        """
        Compute very busy expressions using backward data flow analysis.

        An expression is very busy at a point if on all paths from that point,
        the expression is used before any of its operands are redefined.
        """
        # Collect all expressions
        all_expressions: set[Expression] = set()
        block_use: dict[int, set[Expression]] = {}
        block_kill: dict[int, set[Expression]] = {}

        for block in self.cfg.blocks:
            use: set[Expression] = set()
            kill: set[Expression] = set()
            defined_in_block: set[str] = set()

            # Process statements in reverse order for backward analysis
            for stmt in reversed(block.statements):
                # Find expressions used
                for node in ast.walk(stmt):
                    if isinstance(node, ast.BinOp | ast.Compare | ast.UnaryOp):
                        expr = Expression.from_node(node)
                        all_expressions.add(expr)
                        # Only add to use if not killed after this point
                        if not any(expr.is_killed_by(v) for v in defined_in_block):
                            use.add(expr)

                # Collect definitions
                defined_vars = self._get_defined_vars(stmt)
                for var in defined_vars:
                    defined_in_block.add(var)
                    for expr in all_expressions:
                        if expr.is_killed_by(var):
                            kill.add(expr)

            block_use[block.id] = use
            block_kill[block.id] = kill

        # Initialize
        busy_in: dict[int, set[Expression]] = {}
        busy_out: dict[int, set[Expression]] = {}

        for block in self.cfg.blocks:
            busy_in[block.id] = set()
            busy_out[block.id] = set() if block.is_exit else set(all_expressions)

        # Iterate until fixed point (backward)
        changed = True
        while changed:
            changed = False

            for block in self.cfg.blocks:
                # Intersection of all successors
                if block.successors:
                    new_out = set(all_expressions)
                    for succ in block.successors:
                        new_out &= busy_in[succ.id]
                    if new_out != busy_out[block.id]:
                        busy_out[block.id] = new_out
                        changed = True

                # Transfer: in = use ∪ (out - kill)
                new_in = block_use[block.id] | (busy_out[block.id] - block_kill[block.id])
                if new_in != busy_in[block.id]:
                    busy_in[block.id] = new_in
                    changed = True

        return busy_out

    def _get_defined_vars(self, stmt: ast.stmt) -> set[str]:
        """Get variables defined in a statement."""
        defined: set[str] = set()
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                self._collect_names(target, defined)
        elif isinstance(stmt, ast.AnnAssign) and stmt.target:
            self._collect_names(stmt.target, defined)
        elif isinstance(stmt, ast.AugAssign):
            self._collect_names(stmt.target, defined)
        elif isinstance(stmt, ast.For | ast.AsyncFor):
            self._collect_names(stmt.target, defined)
        elif isinstance(stmt, ast.With | ast.AsyncWith):
            for item in stmt.items:
                if item.optional_vars:
                    self._collect_names(item.optional_vars, defined)
        return defined

    def _collect_names(self, target: ast.AST, names: set[str]) -> None:
        """Collect variable names from an assignment target."""
        if isinstance(target, ast.Name):
            names.add(target.id)
        elif isinstance(target, ast.Tuple | ast.List):
            for elt in target.elts:
                self._collect_names(elt, names)


# =============================================================================
# Utility Functions
# =============================================================================


def get_qualified_name(node: ast.AST, parents: list[ast.AST]) -> str:
    """
    Get the qualified name for a node based on its parent chain.

    Constructs dot-separated qualified names like "Class.method" or "outer_func.inner_func"
    by walking the parent chain and collecting names from function/class definitions.
    """
    parts = []
    for parent in parents:
        if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            parts.append(parent.name)
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        parts.append(node.name)
    return ".".join(parts) if parts else ""


def is_dunder(name: str) -> bool:
    """Check if a name is a dunder (double underscore) name."""
    return name.startswith("__") and name.endswith("__") and len(name) > 4


def is_private(name: str) -> bool:
    """Check if a name is private (starts with underscore)."""
    return name.startswith("_") and not is_dunder(name)
