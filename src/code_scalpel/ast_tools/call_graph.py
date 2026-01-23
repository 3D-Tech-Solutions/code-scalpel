from __future__ import annotations

import ast
import os
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

# [20251213_FEATURE] v1.5.0 - Enhanced call graph with line numbers and Mermaid support


@dataclass
class CallContext:
    """Context information about where a call is made.

    Server-side serialization expects this to exist for v3.3.0 pre-release
    get_call_graph outputs; builders may leave it as defaults.
    """

    in_loop: bool = False
    in_try_block: bool = False
    in_conditional: bool = False
    condition_summary: str | None = None
    in_async: bool = False
    in_except_handler: bool = False


@dataclass
class CallNode:
    """A node in the call graph with location information."""

    name: str
    file: str
    line: int
    end_line: int | None = None
    is_entry_point: bool = False
    # [20260111_BUGFIX] v3.3.0 - MCP server expects source_uri for serialization
    source_uri: str | None = None


@dataclass
class CallEdge:
    """An edge in the call graph representing a call relationship."""

    caller: str
    callee: str
    confidence: float = 1.0
    inference_source: str = "static"
    call_line: int | None = None
    context: CallContext | None = None


@dataclass
class CallGraphResult:
    """Result of call graph analysis."""

    nodes: list[CallNode] = field(default_factory=list)
    edges: list[CallEdge] = field(default_factory=list)
    entry_point: str | None = None
    depth_limit: int | None = None
    mermaid: str = ""
    # [20251225_FEATURE] Tier-friendly metadata for truncation and summaries
    total_nodes: int = 0
    total_edges: int = 0
    nodes_truncated: bool = False
    edges_truncated: bool = False


class CallGraphBuilder:
    """
    Builds a static call graph for a Python project.
    """

    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.definitions: dict[str, set[str]] = {}  # file_path -> set of defined functions/classes
        self.calls: dict[str, list[str]] = {}  # "file:function" -> list of called function names
        self.imports: dict[str, dict[str, str]] = {}  # file_path -> { alias -> full_name }

        # [20251231_FEATURE] v1.0 - JS/TS support for get_call_graph
        # Raw JS/TS import metadata: file -> local_name -> (module_spec, imported_name)
        self._js_imports_raw: dict[str, dict[str, tuple[str, str]]] = {}
        # Export index: file -> exported symbol names
        self._js_exports: dict[str, set[str]] = {}

    def build(self, advanced_resolution: bool = False) -> dict[str, list[str]]:
        """Build the call graph.

        Returns an adjacency list: {"module:caller": ["module:callee", ...]}
        """

        for file_path in self._iter_source_files():
            rel_path = str(file_path.relative_to(self.root_path))
            suffix = file_path.suffix.lower()

            if suffix == ".py":
                try:
                    with open(file_path, encoding="utf-8") as f:
                        code = f.read()
                    tree = ast.parse(code)
                    self._analyze_definitions(tree, rel_path)
                except Exception:
                    continue
            elif suffix in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
                self._analyze_definitions_js_ts(file_path, rel_path)

        # 2. Second pass: Analyze calls and resolve them
        graph: dict[str, list[str]] = {}
        for file_path in self._iter_source_files():
            rel_path = str(file_path.relative_to(self.root_path))
            suffix = file_path.suffix.lower()

            if suffix == ".py":
                try:
                    with open(file_path, encoding="utf-8") as f:
                        code = f.read()
                    tree = ast.parse(code)
                    file_calls = self._analyze_calls(
                        tree,
                        rel_path,
                        advanced_resolution=advanced_resolution,
                    )
                    graph.update(file_calls)
                except Exception:
                    continue
            elif suffix in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
                file_calls = self._analyze_calls_js_ts(
                    file_path,
                    rel_path,
                    advanced_resolution=advanced_resolution,
                )
                graph.update(file_calls)

        return graph

    def _iter_source_files(self):
        skip_dirs = {
            ".git",
            ".venv",
            "venv",
            "__pycache__",
            "node_modules",
            "dist",
            "build",
        }
        for root, dirs, files in os.walk(self.root_path):
            dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
            for file in files:
                lower = file.lower()
                if lower.endswith(
                    (
                        ".py",
                        ".js",
                        ".jsx",
                        ".ts",
                        ".tsx",
                        ".mjs",
                        ".cjs",
                    )
                ):
                    yield Path(root) / file

    def _analyze_definitions_js_ts(self, file_path: Path, rel_path: str) -> None:
        """Extract JS/TS definitions and import/export metadata.

        Prefers tree-sitter (when available) and falls back to the Esprima-based
        parser shipped with Code Scalpel.
        """
        # ------------------------------------------------------------------
        # Tree-sitter path (preferred)
        # ------------------------------------------------------------------
        try:
            from code_scalpel.code_parsers.javascript_parsers.javascript_parsers_treesitter import (
                TREE_SITTER_AVAILABLE,
                TreeSitterJSParser,
            )
        except Exception:
            TREE_SITTER_AVAILABLE = False
            TreeSitterJSParser = None  # type: ignore[assignment]

        if TREE_SITTER_AVAILABLE and TreeSitterJSParser is not None:
            try:
                parser = TreeSitterJSParser()
                result = parser.parse_file(str(file_path))
            except Exception:
                result = None

            if result is not None:
                # Definitions
                self.definitions[rel_path] = set()
                for sym in result.symbols:
                    if sym.kind == "function":
                        self.definitions[rel_path].add(sym.name)
                    elif sym.kind == "class":
                        self.definitions[rel_path].add(sym.name)
                    elif sym.kind == "method" and sym.parent_name:
                        self.definitions[rel_path].add(f"{sym.parent_name}.{sym.name}")

                # Imports (raw)
                self._js_imports_raw.setdefault(rel_path, {})
                for imp in result.imports:
                    module = imp.module
                    # import foo from './x'
                    if imp.default_import:
                        self._js_imports_raw[rel_path][imp.default_import] = (
                            module,
                            "<default>",
                        )
                    # import * as ns from './x'
                    if imp.namespace_import:
                        self._js_imports_raw[rel_path][imp.namespace_import] = (
                            module,
                            "*",
                        )
                    # import { a as b } from './x'
                    for name, alias in imp.named_imports:
                        local = alias or name
                        self._js_imports_raw[rel_path][local] = (module, name)

                # Exports index (best-effort)
                self._js_exports.setdefault(rel_path, set())
                for ex in result.exports:
                    if ex.name:
                        self._js_exports[rel_path].add(ex.name)
                    if ex.kind == "default":
                        self._js_exports[rel_path].add("<default>")
                return

        # ------------------------------------------------------------------
        # Esprima fallback (portable)
        # ------------------------------------------------------------------
        try:
            import esprima  # type: ignore[import-untyped]
            import esprima.nodes  # type: ignore[import-untyped]
        except Exception:
            return

        try:
            code = file_path.read_text(encoding="utf-8")
        except Exception:
            return

        try:
            # Prefer module parsing so `import`/`export` works.
            ast_js = esprima.parseModule(code, loc=True, tolerant=True)
        except Exception:
            try:
                ast_js = esprima.parseScript(code, loc=True, tolerant=True)
            except Exception:
                return

        def _children(n):
            if isinstance(n, list):
                for item in n:
                    if isinstance(item, esprima.nodes.Node):
                        yield item
                return
            if not isinstance(n, esprima.nodes.Node):
                return

            # [20260102_REFACTOR] Avoid shadowing the imported esprima field helper
            for node_field in n.__dict__.values():
                if isinstance(node_field, esprima.nodes.Node):
                    yield node_field
                elif isinstance(node_field, list):
                    for item in node_field:
                        if isinstance(item, esprima.nodes.Node):
                            yield item

        # Definitions
        self.definitions[rel_path] = set()
        stack: list[esprima.nodes.Node] = [ast_js]
        while stack:
            cur = stack.pop()
            if isinstance(cur, esprima.nodes.FunctionDeclaration):
                func_id = getattr(cur, "id", None)
                name = getattr(func_id, "name", None)
                if name:
                    self.definitions[rel_path].add(name)
            for ch in _children(cur):
                stack.append(ch)

        # Imports (raw)
        self._js_imports_raw.setdefault(rel_path, {})
        stack: list[esprima.nodes.Node] = [ast_js]
        while stack:
            cur = stack.pop()
            if isinstance(cur, esprima.nodes.ImportDeclaration):
                module_val = getattr(getattr(cur, "source", None), "value", None)
                module = str(module_val) if module_val is not None else ""
                for spec in getattr(cur, "specifiers", []) or []:
                    if isinstance(spec, esprima.nodes.ImportDefaultSpecifier):
                        local = getattr(getattr(spec, "local", None), "name", None)
                        if local:
                            self._js_imports_raw[rel_path][local] = (
                                module,
                                "<default>",
                            )
                    elif isinstance(spec, esprima.nodes.ImportNamespaceSpecifier):
                        local = getattr(getattr(spec, "local", None), "name", None)
                        if local:
                            self._js_imports_raw[rel_path][local] = (module, "*")
                    elif isinstance(spec, esprima.nodes.ImportSpecifier):
                        imported = getattr(getattr(spec, "imported", None), "name", None)
                        local = getattr(getattr(spec, "local", None), "name", None) or imported
                        if imported and local:
                            self._js_imports_raw[rel_path][local] = (
                                module,
                                str(imported),
                            )

            for ch in _children(cur):
                stack.append(ch)

        # Exports index (best-effort)
        self._js_exports.setdefault(rel_path, set())
        stack: list[esprima.nodes.Node] = [ast_js]
        while stack:
            cur = stack.pop()
            if isinstance(cur, esprima.nodes.ExportDefaultDeclaration):
                self._js_exports[rel_path].add("<default>")
                decl = getattr(cur, "declaration", None)
                name = getattr(getattr(decl, "id", None), "name", None)
                if name:
                    self._js_exports[rel_path].add(name)
            elif isinstance(cur, esprima.nodes.ExportNamedDeclaration):
                decl = getattr(cur, "declaration", None)
                exported_name = getattr(getattr(decl, "id", None), "name", None)
                if exported_name:
                    self._js_exports[rel_path].add(exported_name)
                for spec in getattr(cur, "specifiers", []) or []:
                    exported = getattr(getattr(spec, "exported", None), "name", None)
                    if exported:
                        self._js_exports[rel_path].add(exported)

            for ch in _children(cur):
                stack.append(ch)

    def _resolve_js_module_path(self, from_file: str, module_spec: str) -> str | None:
        """Resolve a relative JS/TS module specifier to a project-relative file path."""
        if not module_spec or not module_spec.startswith("."):
            return None

        base_dir = (self.root_path / from_file).parent
        # Handle './x', './x.js', './x.ts', './x/index.js', etc.
        candidate_bases = [module_spec]
        if not any(module_spec.endswith(ext) for ext in (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")):
            candidate_bases.extend([module_spec + ext for ext in (".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs")])

        candidates: list[Path] = []
        for base in candidate_bases:
            candidates.append((base_dir / base).resolve())
        # index.* fallback
        if module_spec and not module_spec.endswith((".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs")):
            for ext in (".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"):
                candidates.append((base_dir / module_spec / f"index{ext}").resolve())

        for p in candidates:
            try:
                if p.exists() and p.is_file() and self.root_path in p.parents:
                    return str(p.relative_to(self.root_path))
            except Exception:
                continue
        return None

    def _analyze_calls_js_ts(
        self,
        file_path: Path,
        rel_path: str,
        advanced_resolution: bool = False,
    ) -> dict[str, list[str]]:
        """Build per-file call graph for JS/TS.

        Prefers tree-sitter (when available) and falls back to Esprima.
        """
        # ------------------------------------------------------------------
        # Tree-sitter path (preferred)
        # ------------------------------------------------------------------
        try:
            from code_scalpel.code_parsers.javascript_parsers.javascript_parsers_treesitter import (
                TREE_SITTER_AVAILABLE,
                TreeSitterJSParser,
            )
        except Exception:
            TREE_SITTER_AVAILABLE = False
            TreeSitterJSParser = None  # type: ignore[assignment]

        if TREE_SITTER_AVAILABLE and TreeSitterJSParser is not None:
            try:
                parser = TreeSitterJSParser()
                result = parser.parse_file(str(file_path))
                root = result.root_node
            except Exception:
                result = None
                root = None
        else:
            result = None
            root = None

        def _resolve_callee(raw_callee: str, caller_parent: str | None) -> str:
            # Resolve this.method() to Class.method when inside a class method.
            if advanced_resolution and caller_parent and raw_callee.startswith("this."):
                return f"{rel_path}:{caller_parent}.{raw_callee.split('.', 1)[1]}"

            # Local direct definition in same file
            if raw_callee in self.definitions.get(rel_path, set()):
                return f"{rel_path}:{raw_callee}"

            if advanced_resolution:
                # Resolve namespace imports: ns.foo()
                if "." in raw_callee:
                    base, member = raw_callee.split(".", 1)
                    imp = self._js_imports_raw.get(rel_path, {}).get(base)
                    if imp and imp[1] == "*":
                        mod = self._resolve_js_module_path(rel_path, imp[0])
                        if mod and member in self._js_exports.get(mod, set()):
                            return f"{mod}:{member}"

                # Resolve imported identifiers
                imp = self._js_imports_raw.get(rel_path, {}).get(raw_callee)
                if imp:
                    module_spec, imported_name = imp
                    mod = self._resolve_js_module_path(rel_path, module_spec)
                    if mod:
                        if imported_name == "<default>":
                            return f"{mod}:<default>"
                        if imported_name in self._js_exports.get(mod, set()):
                            return f"{mod}:{imported_name}"
                        # Best-effort even if exports index is incomplete
                        return f"{mod}:{imported_name}"

            return raw_callee

        # [20260122_BUGFIX] Ensure tree-sitter call extraction runs instead of falling through to Esprima.
        if result is not None and root is not None:
            # Build a list of callable symbol ranges for caller attribution
            callable_ranges: list[tuple[int, int, str, str | None]] = []
            for sym in result.symbols:
                if sym.kind == "function":
                    end_line = sym.end_line or sym.line
                    callable_ranges.append((sym.line, end_line, sym.name, None))
                elif sym.kind == "method" and sym.parent_name:
                    end_line = sym.end_line or sym.line
                    callable_ranges.append((sym.line, end_line, sym.name, sym.parent_name))

            def _caller_for_line(line: int) -> tuple[str, str | None] | None:
                # Choose the smallest enclosing range (most specific)
                best: tuple[int, int, str, str | None] | None = None
                for start, end, name, parent in callable_ranges:
                    if start <= line <= end:
                        if best is None or (end - start) < (best[1] - best[0]):
                            best = (start, end, name, parent)
                if best is None:
                    return None
                return (best[2], best[3])

            def _callee_from_call(node) -> str | None:
                # call_expression: function field
                fn = node.child_by_field("function")
                if not fn:
                    return None
                # Identifier call
                if fn.type == "identifier":
                    return str(fn.text)
                # member_expression: obj.prop
                if fn.type == "member_expression":
                    obj = fn.child_by_field("object")
                    prop = fn.child_by_field("property")
                    if obj and prop:
                        return f"{str(obj.text)}.{str(prop.text)}"
                    return str(fn.text)
                return str(fn.text)

            # Walk tree to find call expressions
            file_graph: dict[str, list[str]] = {}

            def visit(node) -> None:
                if node.type in {"call_expression", "new_expression"}:
                    line = getattr(node, "start_line", None)
                    if isinstance(line, int):
                        caller = _caller_for_line(line)
                        if caller:
                            caller_name, caller_parent = caller
                            caller_key = (
                                f"{rel_path}:{caller_parent}.{caller_name}"
                                if caller_parent
                                else f"{rel_path}:{caller_name}"
                            )
                            raw = _callee_from_call(node)
                            if raw:
                                file_graph.setdefault(caller_key, []).append(_resolve_callee(raw, caller_parent))

                for child in getattr(node, "named_children", []) or []:
                    visit(child)

            visit(root)
            return file_graph

        # ------------------------------------------------------------------
        # Esprima fallback
        # ------------------------------------------------------------------
        try:
            import esprima  # type: ignore[import-untyped]
            import esprima.nodes  # type: ignore[import-untyped]
        except Exception:
            return {}

        try:
            code = file_path.read_text(encoding="utf-8")
        except Exception:
            return {}

        try:
            ast_js = esprima.parseModule(code, loc=True, tolerant=True)
        except Exception:
            try:
                ast_js = esprima.parseScript(code, loc=True, tolerant=True)
            except Exception:
                return {}

        def _children(n):
            if isinstance(n, list):
                for item in n:
                    if isinstance(item, esprima.nodes.Node):
                        yield item
                return
            if not isinstance(n, esprima.nodes.Node):
                return

            # [20260102_REFACTOR] Avoid shadowing the imported esprima field helper
            for node_field in n.__dict__.values():
                if isinstance(node_field, esprima.nodes.Node):
                    yield node_field
                elif isinstance(node_field, list):
                    for item in node_field:
                        if isinstance(item, esprima.nodes.Node):
                            yield item

        def _callee_name(call_node) -> str | None:
            callee = getattr(call_node, "callee", None)
            if isinstance(callee, esprima.nodes.Identifier):
                return callee.name
            if isinstance(callee, esprima.nodes.MemberExpression):
                obj = getattr(callee, "object", None)
                prop = getattr(callee, "property", None)
                if isinstance(obj, esprima.nodes.Identifier) and isinstance(  # type: ignore[attr-defined]
                    prop, esprima.nodes.Identifier
                ):  # type: ignore[attr-defined]
                    return f"{obj.name}.{prop.name}"
            return None

        file_graph: dict[str, list[str]] = {}

        # Walk while tracking current function context.
        stack: list[tuple[object, str]] = [(ast_js, "<global>")]
        while stack:
            cur, current_fn = stack.pop()
            if isinstance(cur, esprima.nodes.FunctionDeclaration):
                name = getattr(getattr(cur, "id", None), "name", None) or "<anonymous>"
                # Traverse into the function body with new context.
                for ch in _children(cur):
                    stack.append((ch, name))
                continue

            if isinstance(cur, (esprima.nodes.CallExpression, esprima.nodes.NewExpression)):
                raw = _callee_name(cur)
                if raw and current_fn not in {"<global>", "<anonymous>", "<arrow>"}:
                    caller_key = f"{rel_path}:{current_fn}"
                    file_graph.setdefault(caller_key, []).append(_resolve_callee(raw, None))

            for ch in _children(cur):
                stack.append((ch, current_fn))

        return file_graph

    def _iter_python_files(self):
        """
        Iterate over all Python files in the project, skipping hidden/ignored dirs.

        Yields:
            Path: Absolute path to each Python file
        """
        skip_dirs = {
            ".git",
            ".venv",
            "venv",
            "__pycache__",
            "node_modules",
            "dist",
            "build",
        }
        for root, dirs, files in os.walk(self.root_path):
            dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
            for file in files:
                if file.endswith(".py"):
                    yield Path(root) / file

    def _analyze_definitions(self, tree: ast.AST, rel_path: str):
        """
        Extract function/class definitions and imports.

        Args:
            tree: AST of the file
            rel_path: Relative path of the file
        """
        self.definitions[rel_path] = set()
        self.imports[rel_path] = {}

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.definitions[rel_path].add(node.name)
            elif isinstance(node, ast.ClassDef):
                self.definitions[rel_path].add(node.name)
                # Also add methods
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        self.definitions[rel_path].add(f"{node.name}.{item.name}")

            # Collect imports for resolution
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    asname = alias.asname or name
                    self.imports[rel_path][asname] = name
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    name = alias.name
                    asname = alias.asname or name
                    full_name = f"{module}.{name}" if module else name
                    self.imports[rel_path][asname] = full_name

    def _analyze_calls(
        self,
        tree: ast.AST,
        rel_path: str,
        advanced_resolution: bool = False,
    ) -> dict[str, list[str]]:
        """
        Extract calls from functions and resolve them.

        Args:
            tree: AST of the file
            rel_path: Relative path of the file

        Returns:
            Dictionary mapping function keys to list of called function names
        """
        file_graph = {}

        class CallVisitor(ast.NodeVisitor):
            def __init__(self, builder, current_file):
                self.builder = builder
                self.current_file = current_file
                self.current_scope: str | None = None
                self.calls: list[str] = []

                # [20251225_FEATURE] Pro+ scoped method resolution (best-effort)
                self._advanced_resolution = advanced_resolution
                self._current_class: str | None = None
                self._var_types: dict[str, str] = {}

            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                if not self._advanced_resolution:
                    self.generic_visit(node)
                    return

                old_class = self._current_class
                self._current_class = node.name
                self.generic_visit(node)
                self._current_class = old_class

            def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
                old_scope = self.current_scope

                if self._advanced_resolution and self._current_class:
                    self.current_scope = f"{self._current_class}.{node.name}"
                else:
                    self.current_scope = node.name

                self.calls = []
                self._var_types = {}
                self.generic_visit(node)

                # Store calls for this function
                key = f"{self.current_file}:{self.current_scope}"
                file_graph[key] = self.calls

                self.current_scope = old_scope

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                self.visit_FunctionDef(node)

            def visit_Call(self, node: ast.Call) -> None:
                if self.current_scope:
                    callee = self._get_callee_name(node)
                    if callee:
                        resolved = self._resolve_callee(callee)
                        self.calls.append(resolved)
                self.generic_visit(node)

            def visit_Assign(self, node: ast.Assign) -> None:
                if not (self._advanced_resolution and self.current_scope):
                    self.generic_visit(node)
                    return

                # Track simple type assignments: x = ClassName()
                class_name: str | None = None
                if isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Name):
                        class_name = node.value.func.id
                    elif isinstance(node.value.func, ast.Attribute):
                        # module.ClassName() -> take last segment
                        class_name = node.value.func.attr

                if class_name:
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            self._var_types[target.id] = class_name

                self.generic_visit(node)

            def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
                if not (self._advanced_resolution and self.current_scope):
                    self.generic_visit(node)
                    return

                # Track simple annotations: x: ClassName = ...
                if isinstance(node.target, ast.Name):
                    ann = node.annotation
                    if isinstance(ann, ast.Name):
                        self._var_types[node.target.id] = ann.id
                    elif isinstance(ann, ast.Attribute):
                        self._var_types[node.target.id] = ann.attr

                self.generic_visit(node)

            def _get_callee_name(self, node: ast.Call) -> str | None:
                if isinstance(node.func, ast.Name):
                    return node.func.id
                if isinstance(node.func, ast.Attribute):
                    value = self._get_attribute_value(node.func.value)
                    if not value:
                        return None

                    if self._advanced_resolution:
                        # Resolve self.method() -> ClassName.method()
                        if value == "self" and self._current_class:
                            return f"{self._current_class}.{node.func.attr}"
                        # Resolve instance.method() using simple type tracking
                        if value in self._var_types:
                            return f"{self._var_types[value]}.{node.func.attr}"

                    return f"{value}.{node.func.attr}"

                return None

            def _get_attribute_value(self, node):
                if isinstance(node, ast.Name):
                    return node.id
                elif isinstance(node, ast.Attribute):
                    val = self._get_attribute_value(node.value)
                    return f"{val}.{node.attr}" if val else None
                return None

            def _resolve_callee(self, callee):
                # 1. Check local imports
                imports = self.builder.imports.get(self.current_file, {})

                # Case: alias.method() where alias is imported
                parts = callee.split(".")
                if parts[0] in imports:
                    # e.g. "utils.hash" where "import my_utils as utils" -> "my_utils.hash"
                    # or "hash" where "from utils import hash" -> "utils.hash"
                    resolved_base = imports[parts[0]]
                    if len(parts) > 1:
                        return f"{resolved_base}.{'.'.join(parts[1:])}"
                    return resolved_base

                # 2. Check if it's a local definition in the same file
                if callee in self.builder.definitions.get(self.current_file, set()):
                    return f"{self.current_file}:{callee}"

                # 3. Fallback: return as is (likely external lib or built-in)
                return callee

        visitor = CallVisitor(self, rel_path)
        visitor.visit(tree)
        return file_graph

    # [20251213_FEATURE] v1.5.0 - Enhanced call graph methods

    def build_with_details(
        self,
        entry_point: str | None = None,
        depth: int = 10,
        max_nodes: int | None = None,
        advanced_resolution: bool = False,
    ) -> CallGraphResult:
        """
        Build call graph with detailed node and edge information.

        Args:
            entry_point: Starting function (e.g., "main" or "src/app.py:main")
                        If None, includes all functions
            depth: Maximum depth to traverse from entry point (default: 10)

        Returns:
            CallGraphResult with nodes, edges, and Mermaid diagram
        """
        # [20251225_FEATURE] Pro+ may enable improved method/polymorphism resolution
        base_graph = self.build(advanced_resolution=advanced_resolution)

        # Collect node information with line numbers
        node_info: dict[str, CallNode] = {}

        # Python nodes
        for file_path in self._iter_source_files():
            rel_path = str(file_path.relative_to(self.root_path))
            suffix = file_path.suffix.lower()
            if suffix != ".py":
                continue
            try:
                with open(file_path, encoding="utf-8") as f:
                    code = f.read()
                tree = ast.parse(code)

                if advanced_resolution:
                    for top in getattr(tree, "body", []):
                        if isinstance(top, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            key = f"{rel_path}:{top.name}"
                            node_info[key] = CallNode(
                                name=top.name,
                                file=rel_path,
                                line=top.lineno,
                                end_line=getattr(top, "end_lineno", None),
                                is_entry_point=self._is_entry_point(top, tree, rel_path=rel_path),
                            )
                        elif isinstance(top, ast.ClassDef):
                            for item in top.body:
                                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                    qualified = f"{top.name}.{item.name}"
                                    key = f"{rel_path}:{qualified}"
                                    node_info[key] = CallNode(
                                        name=qualified,
                                        file=rel_path,
                                        line=item.lineno,
                                        end_line=getattr(item, "end_lineno", None),
                                        is_entry_point=False,
                                    )
                else:
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            key = f"{rel_path}:{node.name}"
                            node_info[key] = CallNode(
                                name=node.name,
                                file=rel_path,
                                line=node.lineno,
                                end_line=getattr(node, "end_lineno", None),
                                is_entry_point=self._is_entry_point(node, tree, rel_path=rel_path),
                            )
            except Exception:
                continue

        # JS/TS nodes
        tree_sitter_available = False
        TreeSitterJSParser = None  # type: ignore[assignment]
        try:
            from code_scalpel.code_parsers.javascript_parsers.javascript_parsers_treesitter import (
                TREE_SITTER_AVAILABLE,
            )
            from code_scalpel.code_parsers.javascript_parsers.javascript_parsers_treesitter import (
                TreeSitterJSParser as _TSParser,
            )

            tree_sitter_available = bool(TREE_SITTER_AVAILABLE)
            TreeSitterJSParser = _TSParser
        except Exception:
            tree_sitter_available = False

        def _add_js_nodes_esprima(file_path: Path, rel_path: str) -> None:
            try:
                import esprima  # type: ignore[import-untyped]
                import esprima.nodes  # type: ignore[import-untyped]
            except Exception:
                return

            try:
                code = file_path.read_text(encoding="utf-8")
            except Exception:
                return

            try:
                ast_js = esprima.parseModule(code, loc=True, tolerant=True)
            except Exception:
                try:
                    ast_js = esprima.parseScript(code, loc=True, tolerant=True)
                except Exception:
                    return

            def _children(n):
                if isinstance(n, list):
                    for item in n:
                        if isinstance(item, esprima.nodes.Node):
                            yield item
                    return
                if not isinstance(n, esprima.nodes.Node):
                    return
                # [20260102_REFACTOR] Avoid shadowing the imported esprima field helper
                for node_field in n.__dict__.values():
                    if isinstance(node_field, esprima.nodes.Node):
                        yield node_field
                    elif isinstance(node_field, list):
                        for item in node_field:
                            if isinstance(item, esprima.nodes.Node):
                                yield item

            def _callee_ident(call_node) -> str | None:
                callee = getattr(call_node, "callee", None)
                if isinstance(callee, esprima.nodes.Identifier):
                    return callee.name
                return None

            # Determine top-level called identifiers.
            top_level_called: set[str] = set()
            call_stack: list[tuple[esprima.nodes.Node, str]] = [(ast_js, "<global>")]
            while call_stack:
                cur, current_fn = call_stack.pop()
                if isinstance(cur, esprima.nodes.FunctionDeclaration):
                    name = getattr(getattr(cur, "id", None), "name", None) or "<anonymous>"
                    for ch in _children(cur):
                        call_stack.append((ch, name))
                    continue

                if current_fn == "<global>" and isinstance(cur, esprima.nodes.CallExpression):
                    ident = _callee_ident(cur)
                    if ident:
                        top_level_called.add(ident)

                for ch in _children(cur):
                    call_stack.append((ch, current_fn))

            # Extract function declarations.
            func_stack: list[esprima.nodes.Node] = [ast_js]
            while func_stack:
                cur = func_stack.pop()
                if isinstance(cur, esprima.nodes.FunctionDeclaration):
                    name = getattr(getattr(cur, "id", None), "name", None)
                    if name:
                        loc = getattr(cur, "loc", None)
                        start = getattr(loc, "start", None) if loc else None
                        end = getattr(loc, "end", None) if loc else None
                        line = getattr(start, "line", 0) if start else 0
                        end_line = getattr(end, "line", None) if end else None
                        key = f"{rel_path}:{name}"
                        is_entry = name == "main" or name in top_level_called
                        node_info[key] = CallNode(
                            name=name,
                            file=rel_path,
                            line=line,
                            end_line=end_line,
                            is_entry_point=is_entry,
                        )
                for ch in _children(cur):
                    func_stack.append(ch)

        if tree_sitter_available and TreeSitterJSParser is not None:
            js_parser = TreeSitterJSParser()
            for file_path in self._iter_source_files():
                rel_path = str(file_path.relative_to(self.root_path))
                suffix = file_path.suffix.lower()
                if suffix not in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
                    continue
                try:
                    parsed = js_parser.parse_file(str(file_path))
                except Exception:
                    # tree-sitter may be "available" but lack language bindings at runtime.
                    _add_js_nodes_esprima(file_path, rel_path)
                    continue

                # Best-effort JS entry-point detection: functions invoked as direct root statements.
                top_level_called: set[str] = set()
                try:
                    for child in getattr(parsed.root_node, "named_children", []) or []:
                        if child.type != "expression_statement":
                            continue
                        expr = child.child_by_field("expression")
                        if expr and expr.type == "call_expression":
                            fn = expr.child_by_field("function")
                            if fn and fn.type == "identifier":
                                top_level_called.add(str(fn.text))
                except Exception:
                    pass

                for sym in parsed.symbols:
                    if sym.kind == "function":
                        key = f"{rel_path}:{sym.name}"
                        is_entry = sym.name == "main" or sym.name in top_level_called
                        node_info[key] = CallNode(
                            name=sym.name,
                            file=rel_path,
                            line=sym.line,
                            end_line=sym.end_line,
                            is_entry_point=is_entry,
                        )
                    elif sym.kind == "method" and sym.parent_name and advanced_resolution:
                        qualified = f"{sym.parent_name}.{sym.name}"
                        key = f"{rel_path}:{qualified}"
                        node_info[key] = CallNode(
                            name=qualified,
                            file=rel_path,
                            line=sym.line,
                            end_line=sym.end_line,
                            is_entry_point=False,
                        )
        else:
            for file_path in self._iter_source_files():
                rel_path = str(file_path.relative_to(self.root_path))
                suffix = file_path.suffix.lower()
                if suffix not in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
                    continue
                _add_js_nodes_esprima(file_path, rel_path)

        # If entry_point is specified, filter to reachable nodes
        if entry_point:
            reachable = self._get_reachable_nodes(base_graph, entry_point, depth)
        else:
            # "Includes all functions" should include leaf nodes too (nodes with no outgoing edges).
            reachable = set(node_info.keys()) | set(base_graph.keys())

        reachable_list = sorted(reachable)
        total_nodes = len(reachable_list)
        nodes_truncated = False
        if max_nodes is not None and total_nodes > max_nodes:
            reachable_list = reachable_list[:max_nodes]
            nodes_truncated = True

        included = set(reachable_list)

        nodes: list[CallNode] = []
        seen_nodes = set()
        for key in reachable_list:
            if key in node_info:
                nodes.append(node_info[key])
                seen_nodes.add(key)
            else:
                # External or built-in function
                nodes.append(
                    CallNode(
                        name=key.split(":")[-1] if ":" in key else key,
                        file="<external>" if ":" not in key else key.split(":")[0],
                        line=0,
                    )
                )
                seen_nodes.add(key)

        # Build edges list
        edges_full: list[CallEdge] = []
        edges: list[CallEdge] = []
        for caller, callees in base_graph.items():
            if caller not in reachable:
                continue
            for callee in callees:
                edges_full.append(CallEdge(caller=caller, callee=callee))

                # If nodes were truncated, drop edges to truncated nodes.
                if nodes_truncated:
                    if caller not in included:
                        continue
                    if callee in reachable and callee not in included:
                        continue

                edges.append(CallEdge(caller=caller, callee=callee))

        total_edges = len(edges_full)
        edges_truncated = len(edges) != total_edges

        # Generate Mermaid diagram
        mermaid = self._generate_mermaid(nodes, edges, entry_point)

        return CallGraphResult(
            nodes=nodes,
            edges=edges,
            entry_point=entry_point,
            depth_limit=depth,
            mermaid=mermaid,
            total_nodes=total_nodes,
            total_edges=total_edges,
            nodes_truncated=nodes_truncated,
            edges_truncated=edges_truncated,
        )

    def _is_entry_point(
        self,
        func_node: ast.FunctionDef | ast.AsyncFunctionDef,
        tree: ast.AST,
        *,
        rel_path: str | None = None,
    ) -> bool:
        """
        Detect if a function is likely an entry point.

        Entry point heuristics:
        - Function named "main"
        - Function decorated with CLI decorators (click.command, etc.)
        - Function called in if __name__ == "__main__" block
        - [20260121_FEATURE] Test entry points: pytest-style test_* functions in test modules
        """
        if func_node.name == "main":
            return True

        # Heuristic: pytest-style test functions in test files/dirs count as entry points
        if func_node.name.startswith("test_"):
            filename = (rel_path or "").lower()
            if filename.startswith("test_") or "/tests" in filename or "/test_" in filename:
                return True

        # Detect calls in if __name__ == "__main__" blocks
        try:
            for node in ast.walk(tree):
                if not isinstance(node, ast.If):
                    continue

                test = node.test
                if not isinstance(test, ast.Compare):
                    continue

                if not (
                    isinstance(test.left, ast.Name)
                    and test.left.id == "__name__"
                    and len(test.ops) == 1
                    and isinstance(test.ops[0], ast.Eq)
                    and len(test.comparators) == 1
                ):
                    continue

                comp = test.comparators[0]
                value = None
                if isinstance(comp, ast.Constant) and isinstance(comp.value, str):
                    value = comp.value
                elif isinstance(comp, ast.Str):
                    value = comp.s

                if value != "__main__":
                    continue

                for stmt in node.body:
                    for inner in ast.walk(stmt):
                        if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name):
                            if inner.func.id == func_node.name:
                                return True
        except Exception:
            pass

        # Check for CLI decorators
        for decorator in getattr(func_node, "decorator_list", []):
            dec_name = ""
            if isinstance(decorator, ast.Name):
                dec_name = decorator.id
            elif isinstance(decorator, ast.Attribute):
                dec_name = decorator.attr
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    dec_name = decorator.func.attr
                elif isinstance(decorator.func, ast.Name):
                    dec_name = decorator.func.id

            if dec_name in ("command", "main", "cli", "app", "route", "get", "post"):
                return True

        return False

    def _get_reachable_nodes(
        self,
        graph: dict[str, list[str]],
        entry_point: str,
        max_depth: int,
    ) -> set[str]:
        """
        Get all nodes reachable from entry point within depth limit using BFS.
        Handles recursive calls gracefully.

        Args:
            graph: Call graph mapping caller to callees
            entry_point: Starting function key (e.g., "file.py:main")
            max_depth: Maximum depth to traverse

        Returns:
            Set of reachable node keys
        """
        # Normalize entry point (might be just "main" or "file:main")
        if ":" not in entry_point:
            # Find the full key
            for key in graph.keys():
                if key.endswith(f":{entry_point}"):
                    entry_point = key
                    break

        reachable = set()
        queue = deque([(entry_point, 0)])

        while queue:
            node, depth = queue.popleft()

            if node in reachable:
                continue  # Already visited (handles cycles)

            reachable.add(node)

            if depth >= max_depth:
                continue  # Don't explore further

            # Add callees to queue
            for callee in graph.get(node, []):
                if callee not in reachable:
                    queue.append((callee, depth + 1))

        return reachable

    def _generate_mermaid(
        self,
        nodes: list[CallNode],
        edges: list[CallEdge],
        entry_point: str | None,
    ) -> str:
        """
        Generate Mermaid flowchart diagram from call graph.

        Args:
            nodes: List of call nodes to visualize
            edges: List of call edges to visualize
            entry_point: Optional entry point to highlight

        Returns:
            Mermaid diagram syntax
        """

        lines = ["graph TD"]

        # Create node ID mapping (Mermaid doesn't like special chars)
        node_ids: dict[str, str] = {}
        for i, node in enumerate(nodes):
            full_name = f"{node.file}:{node.name}" if node.file != "<external>" else node.name
            node_id = f"N{i}"
            node_ids[full_name] = node_id
            # Also map short names for external refs
            node_ids[node.name] = node_ids.get(node.name, node_id)

        # Add nodes with labels
        for i, node in enumerate(nodes):
            node_id = f"N{i}"
            label = node.name
            if node.line > 0:
                label = f"{node.name}:L{node.line}"

            # Style entry points differently
            if node.is_entry_point or (entry_point and entry_point.endswith(f":{node.name}")):
                lines.append(f'    {node_id}[["{label}"]]')  # Stadium shape for entry
            elif node.file == "<external>":
                lines.append(f"    {node_id}({label})")  # Round for external
            else:
                lines.append(f'    {node_id}["{label}"]')  # Rectangle for internal

        # Add edges
        for edge in edges:
            caller_id = node_ids.get(edge.caller) or node_ids.get(edge.caller.split(":")[-1])
            callee_id = node_ids.get(edge.callee) or node_ids.get(edge.callee.split(":")[-1])

            if caller_id and callee_id:
                lines.append(f"    {caller_id} --> {callee_id}")

        return "\n".join(lines)

    def detect_circular_imports(self) -> list[list[str]]:
        """
        Detect circular import cycles in the project.

        [20251213_FEATURE] P1 - Circular dependency detection

        Returns:
            List of cycles, where each cycle is a list of module paths
            e.g., [["a.py", "b.py", "a.py"], ["c.py", "d.py", "e.py", "c.py"]]
        """

        # Build import graph: module -> modules it imports
        import_graph: dict[str, set[str]] = {}

        for file_path in self._iter_source_files():
            rel_path = str(file_path.relative_to(self.root_path))
            suffix = file_path.suffix.lower()
            try:
                if suffix == ".py":
                    with open(file_path, encoding="utf-8") as f:
                        code = f.read()
                    tree = ast.parse(code)

                    imports = set()
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                # Convert module name to potential file path
                                mod_path = alias.name.replace(".", "/") + ".py"
                                imports.add(mod_path)
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                mod_path = node.module.replace(".", "/") + ".py"
                                imports.add(mod_path)

                    import_graph[rel_path] = imports

                elif suffix in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
                    # Best-effort JS/TS cycle detection via relative imports
                    try:
                        from code_scalpel.code_parsers.javascript_parsers.javascript_parsers_treesitter import (
                            TREE_SITTER_AVAILABLE,
                            TreeSitterJSParser,
                        )
                    except Exception:
                        continue

                    if not TREE_SITTER_AVAILABLE:
                        continue

                    parser = TreeSitterJSParser()
                    result = parser.parse_file(str(file_path))
                    imports = set()
                    for imp in result.imports:
                        mod = self._resolve_js_module_path(rel_path, imp.module)
                        if mod:
                            imports.add(mod)
                    import_graph[rel_path] = imports
            except Exception:
                continue

        # Find cycles using DFS with coloring
        cycles = []
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node: WHITE for node in import_graph}
        path = []

        def dfs(node: str):
            if color[node] == GRAY:
                # Found a cycle - extract it
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return

            if color[node] == BLACK:
                return

            color[node] = GRAY
            path.append(node)

            for neighbor in import_graph.get(node, set()):
                if neighbor in import_graph:  # Only follow internal imports
                    dfs(neighbor)

            path.pop()
            color[node] = BLACK

        for node in import_graph:
            if color[node] == WHITE:
                dfs(node)

        return cycles
