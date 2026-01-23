# Type stubs for javalang library
# This file provides type hints for the javalang library which lacks native stubs
from collections.abc import Iterator
from typing import Any

class Node:
    position: tuple[int, int] | None
    parent: Node | None
    def __init__(self) -> None: ...

class CompilationUnit(Node):
    package: Any
    imports: list[Any]
    types: list[Any]
    def filter(self, node_type: type) -> Iterator[tuple[tuple[Any, ...], Any]]: ...

class Identifier(Node):
    value: str

class ClassDeclaration(Node):
    name: str
    modifiers: list[str] | None
    extends: Any | None
    implements: list[Any] | None
    body: list[Any] | None
    fields: list[FieldDeclaration] | None
    methods: list[MethodDeclaration] | None
    constructors: list[ConstructorDeclaration] | None

class InterfaceDeclaration(Node):
    name: str
    modifiers: list[str] | None
    extends: list[Any] | None
    body: list[Any] | None

class MethodDeclaration(Node):
    name: str
    modifiers: list[str] | None
    return_type: Any | None
    parameters: list[FormalParameter] | None
    body: list[Any] | None
    throws: list[Any] | None

class FieldDeclaration(Node):
    modifiers: list[str] | None
    type: Any
    declarators: list[VariableDeclarator]

class VariableDeclarator(Node):
    name: str
    initializer: Any | None

class FormalParameter(Node):
    name: str
    type: Any
    modifiers: list[str] | None

class ConstructorDeclaration(Node):
    name: str
    modifiers: list[str] | None
    parameters: list[FormalParameter] | None
    body: list[Any] | None

class IfStatement(Node):
    condition: Any
    then_statement: Any
    else_statement: Any | None

class ForStatement(Node):
    control: Any
    body: Any

class WhileStatement(Node):
    condition: Any
    body: Any

class DoStatement(Node):
    condition: Any
    body: Any

class SwitchStatement(Node):
    expression: Any
    cases: list[Any]

class TryStatement(Node):
    block: list[Any] | None
    catches: list[CatchClause] | None
    finally_block: list[Any] | None
    resources: list[Any] | None

class CatchClause(Node):
    parameter: Any
    block: list[Any] | None

class ReturnStatement(Node):
    expression: Any | None

class BreakStatement(Node):
    label: str | None

class ContinueStatement(Node):
    label: str | None

class ThrowStatement(Node):
    expression: Any

class SynchronizedStatement(Node):
    lock: Any
    block: list[Any] | None

class BinaryOperation(Node):
    operator: str
    operandl: Any
    operandr: Any

class TernaryExpression(Node):
    condition: Any
    if_true: Any
    if_false: Any

class Assignment(Node):
    expressionl: Any
    value: Any
    type: str

class MemberReference(Node):
    member: str
    qualifier: str | None

class MethodInvocation(Node):
    member: str
    qualifier: str | None
    arguments: list[Any] | None

class ClassCreator(Node):
    type: Any
    arguments: list[Any] | None

class ArraySelector(Node):
    index: Any

class Literal(Node):
    value: Any

class LambdaExpression(Node):
    parameters: list[Any] | None
    body: Any

class MethodReference(Node):
    expression: Any
    method: Any

class StatementExpression(Node):
    expression: Any

class Statement(Node): ...
