"""Type stubs for esprima.nodes - AST node definitions."""

from typing import Union

class SourceLocation:
    """Source location information."""

    start: Position
    end: Position
    source: str | None

class Position:
    """Position in source code."""

    line: int
    column: int

class Node:
    """Base class for all AST nodes."""

    type: str
    loc: SourceLocation | None
    range: list[int] | None
    parent: Node | None

    def __init__(self) -> None: ...

class Program(Node):
    """Root node of the AST."""

    body: list[Union[Statement, ModuleDeclaration]]
    sourceType: str  # "script" or "module"

class Statement(Node):
    """Base class for statements."""

    pass

class Expression(Node):
    """Base class for expressions."""

    pass

class Pattern(Node):
    """Base class for patterns (destructuring)."""

    pass

class Declaration(Statement):
    """Base class for declarations."""

    pass

class ModuleDeclaration(Node):
    """Base class for module declarations."""

    pass

# Statements
class ExpressionStatement(Statement):
    expression: Expression

class BlockStatement(Statement):
    body: list[Statement]

class EmptyStatement(Statement):
    pass

class DebuggerStatement(Statement):
    pass

class WithStatement(Statement):
    object: Expression
    body: Statement

class ReturnStatement(Statement):
    argument: Expression | None

class LabeledStatement(Statement):
    label: Identifier
    body: Statement

class BreakStatement(Statement):
    label: Identifier | None

class ContinueStatement(Statement):
    label: Identifier | None

class IfStatement(Statement):
    test: Expression
    consequent: Statement
    alternate: Statement | None

class SwitchStatement(Statement):
    discriminant: Expression
    cases: list[SwitchCase]

class SwitchCase(Node):
    test: Expression | None
    consequent: list[Statement]

class ThrowStatement(Statement):
    argument: Expression

class TryStatement(Statement):
    block: BlockStatement
    handler: CatchClause | None
    finalizer: BlockStatement | None

class CatchClause(Node):
    param: Pattern | None
    body: BlockStatement

class WhileStatement(Statement):
    test: Expression
    body: Statement

class DoWhileStatement(Statement):
    body: Statement
    test: Expression

class ForStatement(Statement):
    init: Union[VariableDeclaration, Expression] | None
    test: Expression | None
    update: Expression | None
    body: Statement

class ForInStatement(Statement):
    left: Union[VariableDeclaration, Pattern]
    right: Expression
    body: Statement

class ForOfStatement(Statement):
    left: Union[VariableDeclaration, Pattern]
    right: Expression
    body: Statement
    await_: bool

# Declarations
class FunctionDeclaration(Declaration):
    id: Identifier | None
    params: list[Pattern]
    body: BlockStatement
    generator: bool
    async_: bool
    expression: bool

class VariableDeclaration(Declaration):
    declarations: list[VariableDeclarator]
    kind: str  # "var", "let", "const"

class VariableDeclarator(Node):
    id: Pattern
    init: Expression | None

class ClassDeclaration(Declaration):
    id: Identifier | None
    superClass: Expression | None
    body: ClassBody

class ClassBody(Node):
    body: list[MethodDefinition]

class MethodDefinition(Node):
    key: Expression
    value: FunctionExpression
    kind: str  # "constructor", "method", "get", "set"
    computed: bool
    static: bool

# Expressions
class Identifier(Expression, Pattern):
    name: str

class Literal(Expression):
    value: Union[str, bool, int, float, None]
    raw: str
    regex: dict[str, str] | None

class ThisExpression(Expression):
    pass

class ArrayExpression(Expression):
    elements: list[Expression | None]

class ObjectExpression(Expression):
    properties: list[Property]

class Property(Node):
    key: Expression
    value: Expression
    kind: str  # "init", "get", "set"
    method: bool
    shorthand: bool
    computed: bool

class FunctionExpression(Expression):
    id: Identifier | None
    params: list[Pattern]
    body: BlockStatement
    generator: bool
    async_: bool
    expression: bool

class ArrowFunctionExpression(Expression):
    id: Identifier | None
    params: list[Pattern]
    body: Union[BlockStatement, Expression]
    generator: bool
    async_: bool
    expression: bool

class ClassExpression(Expression):
    id: Identifier | None
    superClass: Expression | None
    body: ClassBody

class TaggedTemplateExpression(Expression):
    tag: Expression
    quasi: TemplateLiteral

class TemplateLiteral(Expression):
    quasis: list[TemplateElement]
    expressions: list[Expression]

class TemplateElement(Node):
    value: dict[str, str]
    tail: bool

class MemberExpression(Expression, Pattern):
    object: Expression
    property: Expression
    computed: bool
    optional: bool

class Super(Node):
    pass

class MetaProperty(Expression):
    meta: Identifier
    property: Identifier

class CallExpression(Expression):
    callee: Union[Expression, Super]
    arguments: list[Expression]
    optional: bool

class NewExpression(Expression):
    callee: Expression
    arguments: list[Expression]

class SpreadElement(Node):
    argument: Expression

class UpdateExpression(Expression):
    operator: str  # "++" or "--"
    argument: Expression
    prefix: bool

class AwaitExpression(Expression):
    argument: Expression

class UnaryExpression(Expression):
    operator: str
    prefix: bool
    argument: Expression

class BinaryExpression(Expression):
    operator: str
    left: Expression
    right: Expression

class LogicalExpression(Expression):
    operator: str  # "||", "&&", "??"
    left: Expression
    right: Expression

class ConditionalExpression(Expression):
    test: Expression
    consequent: Expression
    alternate: Expression

class YieldExpression(Expression):
    argument: Expression | None
    delegate: bool

class AssignmentExpression(Expression):
    operator: str
    left: Pattern
    right: Expression

class SequenceExpression(Expression):
    expressions: list[Expression]

class AssignmentPattern(Pattern):
    left: Pattern
    right: Expression

class ArrayPattern(Pattern):
    elements: list[Pattern | None]

class ObjectPattern(Pattern):
    properties: list[AssignmentProperty]

class AssignmentProperty(Node):
    key: Expression
    value: Pattern
    computed: bool
    shorthand: bool

class RestElement(Pattern):
    argument: Pattern

# Module declarations
class ImportDeclaration(ModuleDeclaration):
    specifiers: list[Union[ImportSpecifier, ImportDefaultSpecifier, ImportNamespaceSpecifier]]
    source: Literal

class ImportSpecifier(Node):
    imported: Identifier
    local: Identifier

class ImportDefaultSpecifier(Node):
    local: Identifier

class ImportNamespaceSpecifier(Node):
    local: Identifier

class ExportAllDeclaration(ModuleDeclaration):
    source: Literal
    exported: Identifier | None

class ExportDefaultDeclaration(ModuleDeclaration):
    declaration: Union[Declaration, Expression]

class ExportNamedDeclaration(ModuleDeclaration):
    declaration: Declaration | None
    specifiers: list[ExportSpecifier]
    source: Literal | None

class ExportSpecifier(Node):
    exported: Identifier
    local: Identifier
