# Type stubs for javalang library
# This file provides type hints for the javalang library which lacks native stubs
from collections.abc import Iterator
from typing import Any

class ast:
    class Node:
        position: tuple[int, int] | None
        def __init__(self) -> None: ...

class tree:
    class CompilationUnit(ast.Node):
        package: Any
        imports: list[Any]
        types: list[Any]
        def filter(self, node_type: type) -> Iterator[tuple[tuple[Any, ...], Any]]: ...

    class Identifier(ast.Node):
        value: str

    class ClassDeclaration(ast.Node):
        name: str
        modifiers: list[str] | None
        extends: Any | None
        implements: list[Any] | None
        body: list[Any] | None
        fields: list[Any] | None
        methods: list[Any] | None
        constructors: list[Any] | None

    class InterfaceDeclaration(ast.Node):
        name: str
        modifiers: list[str] | None
        extends: list[Any] | None
        body: list[Any] | None

    class MethodDeclaration(ast.Node):
        name: str
        modifiers: list[str] | None
        return_type: Any | None
        parameters: list[Any] | None
        body: list[Any] | None
        throws: list[Any] | None

    class FieldDeclaration(ast.Node):
        modifiers: list[str] | None
        type: Any
        declarators: list[Any]

    class VariableDeclarator(ast.Node):
        name: str
        initializer: Any | None

    class FormalParameter(ast.Node):
        name: str
        type: Any
        modifiers: list[str] | None

    class ConstructorDeclaration(ast.Node):
        name: str
        modifiers: list[str] | None
        parameters: list[Any] | None
        body: list[Any] | None

    class IfStatement(ast.Node):
        condition: Any
        then_statement: Any
        else_statement: Any | None

    class ForStatement(ast.Node):
        control: Any
        body: Any

    class WhileStatement(ast.Node):
        condition: Any
        body: Any

    class DoStatement(ast.Node):
        condition: Any
        body: Any

    class SwitchStatement(ast.Node):
        expression: Any
        cases: list[Any]

    class TryStatement(ast.Node):
        block: list[Any] | None
        catches: list[Any] | None
        finally_block: list[Any] | None
        resources: list[Any] | None

    class CatchClause(ast.Node):
        parameter: Any
        block: list[Any] | None

    class ReturnStatement(ast.Node):
        expression: Any | None
        parent: ast.Node | None

    class BreakStatement(ast.Node):
        label: str | None

    class ContinueStatement(ast.Node):
        label: str | None

    class ThrowStatement(ast.Node):
        expression: Any

    class SynchronizedStatement(ast.Node):
        lock: Any
        block: list[Any] | None

    class BinaryOperation(ast.Node):
        operator: str
        operandl: Any
        operandr: Any

    class TernaryExpression(ast.Node):
        condition: Any
        if_true: Any
        if_false: Any

    class Assignment(ast.Node):
        expressionl: Any
        value: Any
        type: str

    class MemberReference(ast.Node):
        member: str
        qualifier: str | None

    class MethodInvocation(ast.Node):
        member: str
        qualifier: str | None
        arguments: list[Any] | None

    class ClassCreator(ast.Node):
        type: Any
        arguments: list[Any] | None

    class ArraySelector(ast.Node):
        index: Any

    class Literal(ast.Node):
        value: Any

    class LambdaExpression(ast.Node):
        parameters: list[Any] | None
        body: Any

    class MethodReference(ast.Node):
        expression: Any
        method: Any

    class StatementExpression(ast.Node):
        expression: Any

    class Statement(ast.Node): ...

class parser:
    class JavaSyntaxError(Exception):
        position: tuple[int, int] | None
        description: str

class parse:
    @staticmethod
    def parse(code: str) -> tree.CompilationUnit: ...
