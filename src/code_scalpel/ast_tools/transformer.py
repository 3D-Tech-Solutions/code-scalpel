from __future__ import annotations

import ast
from collections.abc import Callable
from dataclasses import dataclass

import astor


@dataclass
class TransformationRule:
    """Defines a transformation rule."""

    pattern: str | ast.AST  # Code pattern to match
    replacement: str | ast.AST  # Replacement pattern
    condition: Callable | None = None  # Optional condition for applying the rule


class ASTTransformer(ast.NodeTransformer):
    """Advanced AST transformer with pattern matching and complex transformations."""

    def __init__(self):
        super().__init__()
        self.var_mapping: dict[tuple[str, str], str] = {}
        self.func_mapping: dict[str, str] = {}
        self.transformation_rules: list[TransformationRule] = []
        self.context: list[ast.AST] = []
        self.modified = False

    def add_transformation_rule(self, rule: TransformationRule) -> None:
        """Add a new transformation rule."""
        self.transformation_rules.append(rule)

    def rename_variable(self, old_name: str, new_name: str, scope: str | None = None) -> None:
        """Register a variable rename transformation."""
        self.var_mapping[(old_name, scope if scope else "")] = new_name

    def rename_function(self, old_name: str, new_name: str) -> None:
        """Register a function rename transformation."""
        self.func_mapping[old_name] = new_name

    def visit(self, node: ast.AST) -> ast.AST | None:
        """Enhanced visit method with context tracking."""
        self.context.append(node)
        result = super().visit(node)
        self.context.pop()
        return result

    def visit_Name(self, node: ast.Name) -> ast.AST:
        """Transform variable names with scope awareness."""
        current_scope = self._get_current_scope()

        # Check scoped mapping first, then global mapping
        new_name = self.var_mapping.get((node.id, current_scope)) or self.var_mapping.get((node.id, ""))

        if new_name:
            self.modified = True
            return ast.Name(id=new_name, ctx=node.ctx)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        """Transform function definitions."""
        # Handle function renaming
        new_name = self.func_mapping.get(node.name)
        if new_name:
            self.modified = True
            node.name = new_name

        # Transform function body - filter out None values
        new_body = []
        for stmt in node.body:
            result = self.visit(stmt)
            if result is not None:
                new_body.append(result)  # type: ignore[arg-type]
        node.body = new_body  # type: ignore[assignment]

        # Transform decorators - filter out None values
        if node.decorator_list:
            new_decorators = []
            for d in node.decorator_list:
                result = self.visit(d)
                if result is not None:
                    new_decorators.append(result)  # type: ignore[arg-type]
            node.decorator_list = new_decorators  # type: ignore[assignment]

        return node

    def visit_Call(self, node: ast.Call) -> ast.AST:
        """Transform function calls with pattern matching."""
        for rule in self.transformation_rules:
            if self._matches_pattern(node, rule.pattern):
                if not rule.condition or rule.condition(node):
                    self.modified = True
                    return self._apply_replacement(node, rule.replacement)

        # Transform function name and arguments
        func_result = self.visit(node.func)
        if func_result is not None:
            node.func = func_result  # type: ignore[assignment]

        new_args = []
        for arg in node.args:
            result = self.visit(arg)
            if result is not None:
                new_args.append(result)  # type: ignore[arg-type]
        node.args = new_args  # type: ignore[assignment]

        new_keywords = []
        for kw in node.keywords:
            result = self.visit(kw)
            if result is not None:
                new_keywords.append(result)  # type: ignore[arg-type]
        node.keywords = new_keywords  # type: ignore[assignment]

        return node

    def extract_method(
        self, node: ast.AST, new_func_name: str, args: list[str] | None = None
    ) -> tuple[ast.FunctionDef, ast.Call]:
        """Extract a code block into a new method."""
        # Analyze used variables
        used_vars = set()
        defined_vars = set()

        class VarCollector(ast.NodeVisitor):
            def visit_Name(self, node: ast.Name) -> None:
                if isinstance(node.ctx, ast.Load):
                    used_vars.add(node.id)
                elif isinstance(node.ctx, ast.Store):
                    defined_vars.add(node.id)

        VarCollector().visit(node)

        # Determine parameters
        params = args if args else list(used_vars - defined_vars)

        # Prepare the body - ensure it's a list of statements
        stmt_types = (
            ast.FunctionDef,
            ast.AsyncFunctionDef,
            ast.ClassDef,
            ast.Return,
            ast.Delete,
            ast.Assign,
            ast.AugAssign,
            ast.AnnAssign,
            ast.For,
            ast.AsyncFor,
            ast.While,
            ast.If,
            ast.With,
            ast.AsyncWith,
            ast.Match,
            ast.Raise,
            ast.Try,
            ast.Assert,
            ast.Import,
            ast.ImportFrom,
            ast.Global,
            ast.Nonlocal,
            ast.Expr,
            ast.Pass,
            ast.Break,
            ast.Continue,
        )
        if isinstance(node, stmt_types):
            body_nodes: list[ast.stmt] = [node]  # type: ignore[list-item]
        else:
            body_nodes = [ast.Expr(value=node)]  # type: ignore[arg-type]

        # Create new function
        empty_decorators: list[ast.expr] = []
        func_kwargs = {
            "name": new_func_name,
            "args": ast.arguments(
                args=[ast.arg(arg=p) for p in params],
                posonlyargs=[],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
            ),
            "body": body_nodes,
            "decorator_list": empty_decorators,
            "returns": None,
            "type_comment": None,
        }
        # type_params only available in Python 3.12+
        import sys

        if sys.version_info >= (3, 12):
            func_kwargs["type_params"] = []  # type: ignore[assignment]

        new_func = ast.FunctionDef(**func_kwargs)  # type: ignore[arg-type]

        # Fix missing location information
        ast.fix_missing_locations(new_func)

        # Create function call
        call = ast.Call(
            func=ast.Name(id=new_func_name, ctx=ast.Load()),
            args=[ast.Name(id=p, ctx=ast.Load()) for p in params],
            keywords=[],
        )

        return new_func, call

    def inline_variable(self, node: ast.Name) -> ast.AST | None:
        """Inline a variable's value at its use sites."""
        # Find variable definition
        assignment = self._find_variable_definition(node.id)
        if assignment and isinstance(assignment, ast.Assign):
            return self.visit(assignment.value)
        return None

    def _find_variable_definition(self, var_name: str) -> ast.AST | None:
        """Find the assignment statement that defines a variable."""
        # This is a complex method that would need to traverse the AST
        # to find variable definitions, considering scope and control flow.
        # For now, return None as a placeholder.
        raise NotImplementedError("Variable definition finding not yet implemented")

    def transform_code(self, code: str) -> str:
        """Transform code with all registered transformations."""
        tree: ast.Module = ast.parse(code)
        self.modified = False
        transformed = self.visit(tree)

        if transformed is None:
            transformed = tree

        # Fix any AST inconsistencies
        ast.fix_missing_locations(transformed)

        return astor.to_source(transformed)

    def _matches_pattern(self, node: ast.AST, pattern: str | ast.AST) -> bool:
        """Check if a node matches a pattern."""
        if isinstance(pattern, str):
            parsed: ast.Module = ast.parse(pattern)
            if not parsed.body:
                return False
            pattern_node = parsed.body[0]
            if isinstance(pattern_node, ast.Expr):
                pattern = pattern_node.value
            else:
                pattern = pattern_node

        # Compare AST structures
        return self._compare_nodes(node, pattern)

    def _compare_nodes(self, node1: ast.AST, node2: ast.AST) -> bool:
        """Compare two AST nodes for structural equality."""
        if type(node1) is not type(node2):
            return False

        for field in node1._fields:
            val1 = getattr(node1, field)
            val2 = getattr(node2, field)

            if isinstance(val1, list):
                if not isinstance(val2, list) or len(val1) != len(val2):
                    return False
                for v1, v2 in zip(val1, val2, strict=False):
                    if not self._compare_nodes(v1, v2):
                        return False
            elif isinstance(val1, ast.AST):
                if not self._compare_nodes(val1, val2):
                    return False
            elif val1 != val2:
                return False

        return True

    def _apply_replacement(self, node: ast.AST, replacement: str | ast.AST) -> ast.AST:
        """Apply a replacement pattern."""
        if isinstance(replacement, str):
            parsed: ast.Module = ast.parse(replacement)
            if not parsed.body:
                return node
            replacement_node = parsed.body[0]
            if isinstance(replacement_node, ast.Expr):
                replacement = replacement_node.value
            else:
                replacement = replacement_node

        # Copy relevant attributes from original node
        for attr in ["lineno", "col_offset"]:
            if hasattr(node, attr):
                setattr(replacement, attr, getattr(node, attr))

        return replacement

    def _get_current_scope(self) -> str:
        """Get the name of the current function/class scope."""
        for node in reversed(self.context):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                return node.name
        return ""
