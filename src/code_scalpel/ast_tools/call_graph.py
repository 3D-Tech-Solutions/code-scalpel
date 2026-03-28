from __future__ import annotations

import ast
import os
import re
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

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
    condition_summary: Optional[str] = None
    in_async: bool = False
    in_except_handler: bool = False


@dataclass
class CallNode:
    """A node in the call graph with location information."""

    name: str
    file: str
    line: int
    end_line: Optional[int] = None
    is_entry_point: bool = False
    # [20260111_BUGFIX] v3.3.0 - MCP server expects source_uri for serialization
    source_uri: Optional[str] = None


@dataclass
class CallEdge:
    """An edge in the call graph representing a call relationship."""

    caller: str
    callee: str
    confidence: float = 1.0
    inference_source: str = "static"
    call_line: Optional[int] = None
    context: Optional[CallContext] = None


@dataclass
class CallGraphResult:
    """Result of call graph analysis."""

    nodes: List[CallNode] = field(default_factory=list)
    edges: List[CallEdge] = field(default_factory=list)
    entry_point: Optional[str] = None
    depth_limit: Optional[int] = None
    mermaid: str = ""
    # [20251225_FEATURE] Tier-friendly metadata for truncation and summaries
    total_nodes: int = 0
    total_edges: int = 0
    nodes_truncated: bool = False
    edges_truncated: bool = False


class CallGraphBuilder:
    """
    Builds a static call graph for Python and supported polyglot projects.
    """

    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.definitions: Dict[str, Set[str]] = (
            {}
        )  # file_path -> set of defined functions/classes
        self.calls: Dict[str, List[str]] = (
            {}
        )  # "file:function" -> list of called function names
        self.imports: Dict[str, Dict[str, str]] = (
            {}
        )  # file_path -> { alias -> full_name }

        # [20251231_FEATURE] v1.0 - JS/TS support for get_call_graph
        # Raw JS/TS import metadata: file -> local_name -> (module_spec, imported_name)
        self._js_imports_raw: Dict[str, Dict[str, tuple[str, str]]] = {}
        # Export index: file -> exported symbol names
        self._js_exports: Dict[str, Set[str]] = {}

        # [20260307_FEATURE] Java get_call_graph foundation metadata for package/import resolution.
        self._java_packages: Dict[str, str] = {}
        self._java_imports_raw: Dict[str, list[str]] = {}
        self._java_static_imports_raw: Dict[str, list[str]] = {}
        self._java_types_by_fqcn: Dict[str, str] = {}
        self._java_fqcn_to_local: Dict[str, str] = {}
        self._java_simple_type_index: Dict[str, Set[str]] = {}
        self._java_superclass_refs: Dict[str, str] = {}
        self._java_field_types_by_class: Dict[str, Dict[str, str]] = {}
        self._java_member_selectors_by_class: Dict[str, Dict[str, List[str]]] = {}
        self._java_selector_return_types: Dict[str, str] = {}
        self._java_interface_extends: Dict[str, tuple[list[str], list[str]]] = {}
        self._java_sam_interfaces: Dict[str, tuple[list[str], str, list[str], str]] = {}

        # [20260307_FEATURE] Generic IR-backed get_call_graph fallback for the broader
        # polyglot normalizer set. This provides local callable nodes and same-file
        # call edges for languages that do not yet have handwritten graph resolvers.
        self._ir_modules: Dict[str, object] = {}
        # [20260308_FEATURE] Generic IR import and module indexes for cohort-1
        # cross-file call graph resolution.
        self._ir_languages: Dict[str, str] = {}
        self._ir_import_bindings: Dict[str, Dict[str, tuple[str, str | None, bool]]] = (
            {}
        )
        self._ir_files_by_module_key: Dict[str, Set[str]] = {}
        self._js_ts_alias_resolver = None
        try:
            from code_scalpel.code_parsers.typescript_parsers.alias_resolver import (
                create_alias_resolver,
            )

            # [20260315_FEATURE] Reuse the shared TS alias resolver so JS/TS
            # call-graph edges can follow tsconfig, webpack, or vite path aliases.
            self._js_ts_alias_resolver = create_alias_resolver(root_path)
        except Exception:
            self._js_ts_alias_resolver = None

    _GENERIC_IR_EXTENSION_LANGUAGE_MAP: Dict[str, str] = {
        ".c": "c",
        ".h": "c",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".hpp": "cpp",
        ".hxx": "cpp",
        ".hh": "cpp",
        ".cs": "csharp",
        ".go": "go",
        ".kt": "kotlin",
        ".kts": "kotlin",
        ".php": "php",
        ".phtml": "php",
        ".rb": "ruby",
        ".rake": "ruby",
        ".gemspec": "ruby",
        ".swift": "swift",
        ".rs": "rust",
    }

    def build(self, advanced_resolution: bool = False) -> Dict[str, List[str]]:
        """Build the call graph.

        Returns an adjacency list: {"module:caller": ["module:callee", ...]}
        """

        for file_path in self._iter_source_files():
            rel_path = str(file_path.relative_to(self.root_path))
            suffix = file_path.suffix.lower()

            if suffix == ".py":
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        code = f.read()
                    tree = ast.parse(code)
                    self._analyze_definitions(tree, rel_path)
                except Exception:
                    continue
            elif suffix in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
                self._analyze_definitions_js_ts(file_path, rel_path)
            elif suffix == ".java":
                self._analyze_definitions_java(file_path, rel_path)
            elif suffix in self._GENERIC_IR_EXTENSION_LANGUAGE_MAP:
                self._analyze_definitions_ir(file_path, rel_path)

        # 2. Second pass: Analyze calls and resolve them
        graph: Dict[str, List[str]] = {}
        for file_path in self._iter_source_files():
            rel_path = str(file_path.relative_to(self.root_path))
            suffix = file_path.suffix.lower()

            if suffix == ".py":
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
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
            elif suffix == ".java":
                file_calls = self._analyze_calls_java(
                    file_path,
                    rel_path,
                    advanced_resolution=advanced_resolution,
                )
                graph.update(file_calls)
            elif suffix in self._GENERIC_IR_EXTENSION_LANGUAGE_MAP:
                file_calls = self._analyze_calls_ir(
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
                        ".java",
                        ".c",
                        ".h",
                        ".cpp",
                        ".cc",
                        ".cxx",
                        ".hpp",
                        ".hxx",
                        ".hh",
                        ".cs",
                        ".go",
                        ".kt",
                        ".kts",
                        ".php",
                        ".phtml",
                        ".rb",
                        ".rake",
                        ".gemspec",
                        ".swift",
                        ".rs",
                        ".ts",
                        ".tsx",
                        ".mjs",
                        ".cjs",
                    )
                ):
                    yield Path(root) / file

    # [20260307_FEATURE] Load a normalizer-backed IR module for languages that use
    # the shared polyglot IR but do not yet have dedicated call-graph resolvers.
    def _load_ir_module(self, file_path: Path, rel_path: str):
        """Return an IR module for a supported polyglot file, or None on failure."""
        suffix = file_path.suffix.lower()
        language = self._GENERIC_IR_EXTENSION_LANGUAGE_MAP.get(suffix)
        if language is None:
            return None

        if rel_path in self._ir_modules:
            return self._ir_modules[rel_path]

        try:
            from code_scalpel.ir import normalizers as ir_normalizers
        except Exception:
            return None

        normalizer_name = {
            "c": "CNormalizer",
            "cpp": "CppNormalizer",
            "csharp": "CSharpNormalizer",
            "go": "GoNormalizer",
            "kotlin": "KotlinNormalizer",
            "php": "PHPNormalizer",
            "ruby": "RubyNormalizer",
            "swift": "SwiftNormalizer",
            "rust": "RustNormalizer",
        }.get(language)
        if normalizer_name is None:
            return None

        normalizer_cls = getattr(ir_normalizers, normalizer_name, None)
        if normalizer_cls is None:
            return None

        try:
            code = file_path.read_text(encoding="utf-8")
            module = normalizer_cls().normalize(code, filename=rel_path)
        except Exception:
            return None

        self._ir_modules[rel_path] = module
        return module

    # [20260307_FEATURE] Shared IR traversal for call-graph fallbacks across the
    # broader normalizer-backed language set.
    def _iter_ir_child_nodes(self, value):
        """Yield nested IR nodes from a value, list, or dict."""
        try:
            from code_scalpel.ir.nodes import IRNode
        except Exception:
            return

        if isinstance(value, IRNode):
            yield value
            return
        if isinstance(value, list):
            for item in value:
                yield from self._iter_ir_child_nodes(item)
            return
        if isinstance(value, dict):
            for item in value.values():
                yield from self._iter_ir_child_nodes(item)

    # [20260308_FEATURE] Preserve receiver-backed method names for IR languages that
    # encode methods outside class bodies, such as Go and Kotlin extensions.
    def _extract_ir_receiver_name(self, function_node) -> str | None:
        """Return a normalized receiver/type name from IR function metadata."""
        raw_receiver = getattr(function_node, "_metadata", {}).get("receiver")
        if not isinstance(raw_receiver, str) or not raw_receiver.strip():
            return None

        normalized = raw_receiver.strip()
        normalized = normalized.strip("()")
        normalized = normalized.replace("*", " ")
        normalized = re.sub(r"\b(var|val|mut|const|ref|inout)\b", " ", normalized)
        tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", normalized)
        if not tokens:
            return None
        for token in reversed(tokens):
            if token[:1].isupper():
                return token
        if len(tokens) >= 2:
            return tokens[-1]
        return None

    # [20260308_FEATURE] Canonicalize generic IR callable names consistently across
    # local and import-aware resolution.
    def _qualify_ir_callable_name(
        self, function_node, current_class: str | None = None
    ) -> str | None:
        """Return the canonical graph name for an IR function definition."""
        name = getattr(function_node, "name", "")
        if not name or name.startswith("<"):
            return None
        if current_class:
            return f"{current_class}.{name}"
        receiver_name = self._extract_ir_receiver_name(function_node)
        if receiver_name:
            return f"{receiver_name}.{name}"
        return name

    # [20260308_FEATURE] Flatten IR call targets so member calls participate in the
    # shared generic resolver.
    def _flatten_ir_callable_expr(self, expr) -> str | None:
        """Return a dotted callee string from an IR expression when possible."""
        try:
            from code_scalpel.ir.nodes import IRAttribute, IRName
        except Exception:
            return None

        if isinstance(expr, IRName):
            return str(expr.id)
        if isinstance(expr, IRAttribute):
            base = self._flatten_ir_callable_expr(getattr(expr, "value", None))
            if base:
                return f"{base}.{expr.attr}"
            if expr.attr:
                return expr.attr
        func_id = getattr(expr, "id", None)
        if isinstance(func_id, str):
            return func_id
        attr_name = getattr(expr, "attr", None)
        if isinstance(attr_name, str) and attr_name:
            return attr_name
        return None

    # [20260308_FEATURE] Harvest IR imports so advanced generic resolution can map
    # imported modules and symbols onto project files.
    def _iter_ir_import_nodes(self, module):
        """Yield top-level import nodes from a generic IR module."""
        try:
            from code_scalpel.ir.nodes import IRImport
        except Exception:
            return

        for node in getattr(module, "body", []) or []:
            if isinstance(node, IRImport):
                yield node

    # [20260308_FEATURE] Maintain a best-effort module key index for generic import
    # resolution across the local project.
    def _candidate_ir_module_keys(
        self,
        rel_path: str,
        language: str,
        import_module: str | None = None,
        imported_name: str | None = None,
    ) -> Set[str]:
        """Return lookup keys for a file path or import spec."""
        if import_module is None:
            noext = Path(rel_path).with_suffix("").as_posix()
            if not noext:
                return set()
            parts = [part for part in noext.split("/") if part and part != "index"]
            if not parts:
                parts = [Path(noext).stem]
            candidates = {
                "/".join(parts),
                ".".join(parts),
                "::".join(parts),
                parts[-1],
                f"./{parts[-1]}",
            }
            if language == "rust":
                candidates |= {
                    f"crate::{'::'.join(parts)}",
                    f"crate::{parts[-1]}",
                }
            if language == "php":
                candidates.add("\\".join(parts))
            return {
                item.strip("/")
                for candidate in candidates
                for item in {candidate, candidate.lower()}
                if item.strip("/")
            }

        raw = import_module.strip().strip("\"'")
        if not raw:
            return set()
        raw = raw.lstrip("./")
        if raw.startswith("crate::"):
            raw = raw[len("crate::") :]
        if raw.startswith("self::"):
            raw = raw[len("self::") :]
        if raw.startswith("super::"):
            raw = raw[len("super::") :]

        variants = {
            raw,
            raw.replace("\\", "/"),
            raw.replace("::", "/"),
            raw.replace(".", "/"),
            raw.replace("/", "."),
            raw.replace("/", "::"),
            raw.replace(".", "::"),
        }

        if imported_name:
            imported_name = imported_name.strip("\\")
            expanded: Set[str] = set()
            for variant in list(variants):
                clean = variant.strip("/")
                if not clean:
                    continue
                expanded.add(clean)
                expanded.add(f"{clean}/{imported_name}")
                expanded.add(f"{clean}.{imported_name}")
                expanded.add(f"{clean}::{imported_name}")
                if language == "php":
                    expanded.add(f"{clean}\\{imported_name}")
            variants |= expanded

        return {
            item.strip("/")
            for candidate in variants
            for item in {candidate, candidate.lower()}
            if item.strip("/")
        }

    # [20260308_FEATURE] Convert IR imports into alias bindings for advanced generic
    # resolution while keeping lookups conservative.
    def _build_ir_import_bindings(self, module, rel_path: str, language: str) -> None:
        """Populate alias and module bindings for a generic IR module."""
        bindings: Dict[str, tuple[str, str | None, bool]] = {}

        for import_node in self._iter_ir_import_nodes(module) or []:
            module_spec = getattr(import_node, "module", "") or ""
            names = [name for name in getattr(import_node, "names", []) or [] if name]
            alias = getattr(import_node, "alias", None)
            if names:
                for imported_name in names:
                    local_name = alias or imported_name
                    bindings[local_name] = (module_spec, imported_name, False)
                continue

            if alias:
                bindings[alias] = (module_spec, None, True)

            segments = [
                segment
                for segment in re.split(r"[./:\\\\]+", module_spec)
                if segment and segment not in {"crate", "self", "super"}
            ]
            if not segments:
                continue

            basename = segments[-1]
            bindings.setdefault(basename, (module_spec, None, True))

            if language in {"rust", "kotlin", "php"} and len(segments) >= 2:
                bindings[basename] = ("/".join(segments[:-1]), basename, False)

        self._ir_import_bindings[rel_path] = bindings

    # [20260308_FEATURE] Resolve generic import specs to project files using a
    # best-effort module/file index.
    def _match_ir_import_targets(
        self,
        rel_path: str,
        local_name: str,
        imported_name: str | None = None,
    ) -> List[str]:
        """Return candidate project files for a generic IR import binding."""
        language = self._ir_languages.get(rel_path, "")
        module_spec, binding_imported_name, _is_module_import = (
            self._ir_import_bindings.get(rel_path, {}).get(
                local_name, ("", None, False)
            )
        )
        target_name = imported_name or binding_imported_name
        if binding_imported_name:
            target_name = binding_imported_name
        if not module_spec:
            return []

        matches: Set[str] = set()
        for key in self._candidate_ir_module_keys(
            rel_path,
            language,
            import_module=module_spec,
            imported_name=target_name,
        ):
            matches.update(self._ir_files_by_module_key.get(key, set()))

        return sorted(candidate for candidate in matches if candidate != rel_path)

    # [20260308_FEATURE] Resolve advanced generic import edges conservatively so the
    # cohort-1 runtime slice only claims edges that map cleanly to known files.
    def _resolve_ir_imported_callee(
        self,
        raw_callee: str,
        rel_path: str,
        current_class: str | None,
    ) -> str | None:
        """Resolve a generic IR callee through imported project files."""
        normalized = self._normalize_ir_callee_name(raw_callee)
        head, _sep, tail = normalized.partition(".")
        candidate_files = self._match_ir_import_targets(rel_path, head, tail or None)

        resolved: Set[str] = set()
        for target_file in candidate_files:
            target_definitions = self.definitions.get(target_file, set())
            if not target_definitions:
                continue

            if tail:
                exact_matches = {
                    definition
                    for definition in target_definitions
                    if definition == tail or definition.endswith(f".{tail}")
                }
            else:
                exact_matches = {
                    definition
                    for definition in target_definitions
                    if definition == head
                }

            if not exact_matches and not tail:
                exact_matches = {
                    definition
                    for definition in target_definitions
                    if definition.endswith(f".{head}")
                }

            if len(exact_matches) == 1:
                resolved.add(f"{target_file}:{next(iter(exact_matches))}")

        if len(resolved) == 1:
            return next(iter(resolved))

        if "." not in normalized:
            imported_matches: Set[str] = set()
            for local_name in self._ir_import_bindings.get(rel_path, {}):
                for target_file in self._match_ir_import_targets(rel_path, local_name):
                    target_definitions = self.definitions.get(target_file, set())
                    exact_matches = {
                        definition
                        for definition in target_definitions
                        if definition == normalized
                        or definition.endswith(f".{normalized}")
                    }
                    if len(exact_matches) == 1:
                        imported_matches.add(
                            f"{target_file}:{next(iter(exact_matches))}"
                        )
            if len(imported_matches) == 1:
                return next(iter(imported_matches))

        if current_class and normalized.startswith(("self.", "this.")):
            return None
        return None

    # [20260307_FEATURE] Extract callable details from a normalizer-backed IR module.
    def _iter_ir_callable_details(
        self, module
    ) -> list[tuple[str, int, int | None, bool]]:
        """Return callable names and source locations from a generic IR module."""
        try:
            from code_scalpel.ir.nodes import IRClassDef, IRFunctionDef
        except Exception:
            return []

        details: list[tuple[str, int, int | None, bool]] = []

        def visit(nodes, current_class: str | None = None) -> None:
            for node in nodes or []:
                if isinstance(node, IRClassDef):
                    qualified_class = (
                        f"{current_class}.{node.name}" if current_class else node.name
                    )
                    visit(node.body, qualified_class)
                elif isinstance(node, IRFunctionDef):
                    qualified_name = self._qualify_ir_callable_name(node, current_class)
                    if not qualified_name:
                        continue
                    line = getattr(getattr(node, "loc", None), "line", 0) or 0
                    end_line = getattr(getattr(node, "loc", None), "end_line", None)
                    is_entry = node.name in {"main", "Main"}
                    details.append((qualified_name, line, end_line, is_entry))
                    visit(node.body, current_class)

        visit(getattr(module, "body", []))
        return details

    # [20260307_FEATURE] Populate same-file definitions from normalizer-backed IR modules.
    def _analyze_definitions_ir(self, file_path: Path, rel_path: str) -> None:
        """Extract callable definitions from a generic IR module."""
        module = self._load_ir_module(file_path, rel_path)
        if module is None:
            return

        language = getattr(
            module, "source_language", None
        ) or self._GENERIC_IR_EXTENSION_LANGUAGE_MAP.get(file_path.suffix.lower(), "")
        self._ir_languages[rel_path] = language
        for key in self._candidate_ir_module_keys(rel_path, language):
            self._ir_files_by_module_key.setdefault(key, set()).add(rel_path)

        definitions = {
            callable_name
            for callable_name, _line, _end_line, _is_entry in self._iter_ir_callable_details(
                module
            )
        }
        self.definitions[rel_path] = definitions
        self.imports.setdefault(rel_path, {})
        self._build_ir_import_bindings(module, rel_path, language)

    # [20260307_FEATURE] Normalize IR call names so generic local resolution can map
    # method receivers consistently across languages.
    def _normalize_ir_callee_name(self, callee: str) -> str:
        """Canonicalize a raw IR callee name for same-file lookup."""
        normalized = callee.replace("::", ".").replace("->", ".")
        if normalized.startswith("__new__"):
            return normalized[len("__new__") :]
        return normalized

    # [20260307_FEATURE] Resolve same-file callees for IR-backed fallback languages.
    def _resolve_ir_callee(
        self,
        raw_callee: str,
        rel_path: str,
        current_class: str | None,
        advanced_resolution: bool = False,
    ) -> str:
        """Resolve a generic IR callee against same-file definitions."""
        definitions = self.definitions.get(rel_path, set())
        normalized = self._normalize_ir_callee_name(raw_callee)

        if current_class and normalized.startswith(("self.", "this.")):
            method_name = normalized.split(".", 1)[1]
            candidate = f"{current_class}.{method_name}"
            if candidate in definitions:
                return f"{rel_path}:{candidate}"

        if current_class and "." not in normalized:
            candidate = f"{current_class}.{normalized}"
            if candidate in definitions:
                return f"{rel_path}:{candidate}"

        if normalized in definitions:
            return f"{rel_path}:{normalized}"

        if "." in normalized:
            if normalized in definitions:
                return f"{rel_path}:{normalized}"
            _receiver, member = normalized.rsplit(".", 1)
            suffix_matches = sorted(
                definition
                for definition in definitions
                if definition.endswith(f".{member}")
            )
            if len(suffix_matches) == 1:
                return f"{rel_path}:{suffix_matches[0]}"
        else:
            suffix_matches = sorted(
                definition
                for definition in definitions
                if definition.endswith(f".{normalized}")
            )
            if len(suffix_matches) == 1:
                return f"{rel_path}:{suffix_matches[0]}"

        if advanced_resolution:
            imported = self._resolve_ir_imported_callee(
                raw_callee, rel_path, current_class
            )
            if imported:
                return imported

        return normalized

    # [20260307_FEATURE] Generic local-call graph extraction for normalizer-backed
    # languages beyond Python, JS/TS, and Java.
    def _analyze_calls_ir(
        self,
        file_path: Path,
        rel_path: str,
        advanced_resolution: bool = False,
    ) -> Dict[str, List[str]]:
        """Extract same-file call edges from a normalizer-backed IR module."""
        try:
            from code_scalpel.ir.nodes import IRCall, IRClassDef, IRFunctionDef
        except Exception:
            return {}

        module = self._load_ir_module(file_path, rel_path)
        if module is None:
            return {}

        file_graph: Dict[str, List[str]] = {}

        def callee_name(call_node: IRCall) -> str | None:
            return self._flatten_ir_callable_expr(getattr(call_node, "func", None))

        def collect_calls(node, current_class: str | None, calls: list[str]) -> None:
            if isinstance(node, IRFunctionDef):
                return
            if isinstance(node, IRClassDef):
                return
            if isinstance(node, IRCall):
                raw = callee_name(node)
                if raw:
                    calls.append(
                        self._resolve_ir_callee(
                            raw,
                            rel_path,
                            current_class,
                            advanced_resolution=advanced_resolution,
                        )
                    )
            for child in self._iter_ir_child_nodes(getattr(node, "__dict__", {})):
                collect_calls(child, current_class, calls)

        def visit(nodes, current_class: str | None = None) -> None:
            for node in nodes or []:
                if isinstance(node, IRClassDef):
                    qualified_class = (
                        f"{current_class}.{node.name}" if current_class else node.name
                    )
                    visit(node.body, qualified_class)
                elif isinstance(node, IRFunctionDef):
                    qualified_name = self._qualify_ir_callable_name(node, current_class)
                    if not qualified_name:
                        continue
                    caller_key = f"{rel_path}:{qualified_name}"
                    calls: list[str] = []
                    for body_node in node.body:
                        collect_calls(body_node, current_class, calls)
                    file_graph[caller_key] = calls
                    visit(node.body, current_class)

        visit(getattr(module, "body", []))
        return file_graph

    # [20260307_FEATURE] Builder-first Java graph substrate for Stage 10 runtime work.
    def _load_java_parse_result(self, file_path: Path):
        """Parse a Java file and return the parser plus detailed result."""
        try:
            from code_scalpel.code_parsers.java_parsers.java_parser_treesitter import (
                JavaParser,
            )
        except Exception:
            return None, None

        try:
            code = file_path.read_text(encoding="utf-8")
        except Exception:
            return None, None

        try:
            parser = JavaParser()
            result = parser.parse_detailed(code)
        except Exception:
            return None, None

        return parser, result

    # [20260309_FEATURE] Index project-local Java single-abstract-method interfaces so generic lambda and method-reference typing is not limited to the built-in JDK functional interfaces.
    def _collect_java_sam_interfaces(self, parser, root, rel_path: str) -> None:
        """Collect single-abstract-method interface signatures from a Java AST."""

        def visit(node, prefix: str | None = None) -> None:
            node_type = getattr(node, "type", "")
            if node_type == "interface_declaration":
                name_node = node.child_by_field_name("name")
                interface_name = parser._get_text(name_node) if name_node else ""
                if not interface_name:
                    return
                qualified_name = (
                    f"{prefix}.{interface_name}" if prefix else interface_name
                )
                type_parameters_node = parser._find_child_by_type(
                    node, "type_parameters"
                )
                type_parameters: list[str] = []
                if type_parameters_node is not None:
                    for type_parameter in parser._find_children_by_type(
                        type_parameters_node, "type_parameter"
                    ):
                        param_name = parser._get_text(type_parameter).strip()
                        if param_name:
                            type_parameters.append(param_name)

                extends_interfaces: list[str] = []
                extends_node = parser._find_child_by_type(node, "extends_interfaces")
                if extends_node is not None:
                    type_list = parser._find_child_by_type(extends_node, "type_list")
                    if type_list is not None:
                        for child in getattr(type_list, "children", []) or []:
                            if not getattr(child, "is_named", False):
                                continue
                            if getattr(child, "type", "") in {
                                "type_identifier",
                                "scoped_type_identifier",
                                "generic_type",
                            }:
                                extends_interfaces.append(
                                    parser._get_text(child).strip()
                                )

                self._java_interface_extends[f"{rel_path}:{qualified_name}"] = (
                    type_parameters,
                    extends_interfaces,
                )

                body_node = parser._find_child_by_type(node, "interface_body")
                method_nodes = []
                if body_node is not None:
                    method_nodes = [
                        child
                        for child in getattr(body_node, "children", []) or []
                        if getattr(child, "type", "") == "method_declaration"
                    ]

                if len(method_nodes) == 1:
                    method_node = method_nodes[0]
                    method_name_node = method_node.child_by_field_name("name")
                    method_name = (
                        parser._get_text(method_name_node).strip()
                        if method_name_node is not None
                        else ""
                    )
                    return_type_node = method_node.child_by_field_name("type")
                    return_type = (
                        parser._get_text(return_type_node).strip()
                        if return_type_node is not None
                        else "void"
                    )
                    parameter_types: list[str] = []
                    parameters_node = parser._find_child_by_type(
                        method_node, "formal_parameters"
                    )
                    if parameters_node is not None:
                        for parameter_node in (
                            getattr(parameters_node, "children", []) or []
                        ):
                            if not getattr(parameter_node, "is_named", False):
                                continue
                            if parameter_node.type not in {
                                "formal_parameter",
                                "spread_parameter",
                                "receiver_parameter",
                            }:
                                continue
                            type_node = parameter_node.child_by_field_name("type")
                            parameter_type = (
                                parser._get_text(type_node).strip()
                                if type_node is not None
                                else "?"
                            )
                            parameter_types.append(parameter_type)

                    self._java_sam_interfaces[f"{rel_path}:{qualified_name}"] = (
                        type_parameters,
                        method_name,
                        parameter_types,
                        return_type,
                    )

                if body_node is not None:
                    for child in getattr(body_node, "children", []) or []:
                        if getattr(child, "is_named", False):
                            visit(child, qualified_name)
                return

            nested_prefix = prefix
            if node_type in {"class_declaration", "record_declaration"}:
                name_node = node.child_by_field_name("name")
                owner_name = parser._get_text(name_node) if name_node else ""
                if owner_name:
                    nested_prefix = f"{prefix}.{owner_name}" if prefix else owner_name

            for child in getattr(node, "children", []) or []:
                if getattr(child, "is_named", False):
                    visit(child, nested_prefix)

        visit(root)

    def _normalize_java_selector_type(self, type_name: str | None) -> str:
        """Normalize a Java type name for selector and overload matching."""
        if not type_name:
            return "?"
        normalized = re.sub(r"\s+", "", type_name)
        normalized = re.sub(
            r"([A-Za-z_$][\w$]*\.)+([A-Za-z_$][\w$]*(?:\[\])*)",
            r"\2",
            normalized,
        )
        return normalized or "?"

    def _build_java_selector(
        self,
        qualified_owner: str,
        member_name: str,
        parameters: list[object] | None,
        overloaded_names: set[str],
    ) -> str:
        """Return the canonical Java selector for a method or constructor."""
        if member_name not in overloaded_names:
            return f"{qualified_owner}.{member_name}"
        normalized_parameters = ", ".join(
            self._normalize_java_selector_type(getattr(parameter, "param_type", None))
            for parameter in (parameters or [])
        )
        return f"{qualified_owner}.{member_name}({normalized_parameters})"

    def _java_selector_arity(self, selector: str) -> int | None:
        """Return selector arity for a signature-qualified Java callable."""
        if "(" not in selector or not selector.endswith(")"):
            return None
        argument_block = selector.rsplit("(", 1)[1][:-1]
        if not argument_block:
            return 0
        return len([part for part in argument_block.split(",") if part.strip()])

    def _select_java_selector(
        self,
        selectors: list[str],
        argument_types: list[str] | None = None,
    ) -> str | None:
        """Choose the best Java selector using exact signature then arity fallback."""
        if not selectors:
            return None
        if len(selectors) == 1:
            return selectors[0]

        primitive_box_pairs = {
            "boolean": "Boolean",
            "byte": "Byte",
            "char": "Character",
            "short": "Short",
            "int": "Integer",
            "long": "Long",
            "float": "Float",
            "double": "Double",
        }
        boxing_aliases = {primitive: primitive for primitive in primitive_box_pairs}
        boxing_aliases.update(
            {boxed: primitive for primitive, boxed in primitive_box_pairs.items()}
        )

        def normalize_for_match(type_name: str) -> str:
            normalized = self._normalize_java_selector_type(type_name)
            return boxing_aliases.get(normalized, normalized)

        def selector_argument_types(selector: str) -> list[str] | None:
            if "(" not in selector or not selector.endswith(")"):
                return None
            argument_block = selector.rsplit("(", 1)[1][:-1].strip()
            if not argument_block:
                return []
            return [
                normalize_for_match(part.strip())
                for part in argument_block.split(",")
                if part.strip()
            ]

        normalized_arguments = [
            normalize_for_match(argument_type)
            for argument_type in (argument_types or [])
        ]
        if normalized_arguments:
            exact_suffix = f"({', '.join(normalized_arguments)})"
            exact_matches = [
                selector for selector in selectors if selector.endswith(exact_suffix)
            ]
            if len(exact_matches) == 1:
                return exact_matches[0]

            compatible_matches = [
                selector
                for selector in selectors
                if selector_argument_types(selector) == normalized_arguments
            ]
            if len(compatible_matches) == 1:
                return compatible_matches[0]

            arity_matches = [
                selector
                for selector in selectors
                if self._java_selector_arity(selector) == len(normalized_arguments)
            ]
            if len(arity_matches) == 1:
                return arity_matches[0]

        unsuffixed = [selector for selector in selectors if "(" not in selector]
        if len(unsuffixed) == 1:
            return unsuffixed[0]

        return None

    def _iter_java_callable_metadata(
        self, result
    ) -> list[tuple[str, str, str, int, int | None, bool, str | None]]:
        """Return canonical Java callable metadata from a parse result."""
        callables: list[tuple[str, str, str, int, int | None, bool, str | None]] = []

        def add_class(class_info, prefix: str | None = None) -> None:
            qualified_class = (
                f"{prefix}.{class_info.name}" if prefix else class_info.name
            )
            overloaded_names: dict[str, int] = {}
            for method in getattr(class_info, "methods", []) or []:
                member_name = (
                    class_info.name
                    if getattr(method, "is_constructor", False)
                    else method.name
                )
                overloaded_names[member_name] = overloaded_names.get(member_name, 0) + 1
            overloaded_member_names = {
                member_name
                for member_name, count in overloaded_names.items()
                if count > 1
            }

            for method in getattr(class_info, "methods", []) or []:
                member_name = (
                    class_info.name
                    if getattr(method, "is_constructor", False)
                    else method.name
                )
                callable_name = self._build_java_selector(
                    qualified_class,
                    member_name,
                    getattr(method, "parameters", []),
                    overloaded_member_names,
                )
                is_entry_point = method.name == "main"
                if getattr(method, "is_constructor", False):
                    is_entry_point = False
                callables.append(
                    (
                        qualified_class,
                        member_name,
                        callable_name,
                        method.line,
                        method.end_line or None,
                        is_entry_point,
                        (
                            qualified_class.split(".")[-1]
                            if getattr(method, "is_constructor", False)
                            else getattr(method, "return_type", None)
                        ),
                    )
                )

            for inner_class in getattr(class_info, "inner_classes", []) or []:
                add_class(inner_class, qualified_class)

            for inner_record in getattr(class_info, "inner_records", []) or []:
                add_record(inner_record, qualified_class)

        def add_record(record_info, prefix: str | None = None) -> None:
            qualified_record = (
                f"{prefix}.{record_info.name}" if prefix else record_info.name
            )
            overloaded_names: dict[str, int] = {}
            for method in getattr(record_info, "methods", []) or []:
                member_name = (
                    record_info.name
                    if getattr(method, "is_constructor", False)
                    else method.name
                )
                overloaded_names[member_name] = overloaded_names.get(member_name, 0) + 1
            overloaded_member_names = {
                member_name
                for member_name, count in overloaded_names.items()
                if count > 1
            }
            for method in getattr(record_info, "methods", []) or []:
                member_name = (
                    record_info.name
                    if getattr(method, "is_constructor", False)
                    else method.name
                )
                callable_name = self._build_java_selector(
                    qualified_record,
                    member_name,
                    getattr(method, "parameters", []),
                    overloaded_member_names,
                )
                callables.append(
                    (
                        qualified_record,
                        member_name,
                        callable_name,
                        method.line,
                        method.end_line or None,
                        False,
                        (
                            qualified_record.split(".")[-1]
                            if getattr(method, "is_constructor", False)
                            else getattr(method, "return_type", None)
                        ),
                    )
                )

        for class_info in getattr(result, "classes", []) or []:
            add_class(class_info)

        for record_info in getattr(result, "records", []) or []:
            add_record(record_info)

        return callables

    # [20260307_FEATURE] Canonical Java callable details for graph node emission.
    def _iter_java_callable_details(
        self, result
    ) -> list[tuple[str, int, int | None, bool]]:
        """Return canonical Java callable details from a parse result."""
        return [
            (selector, line, end_line, is_entry_point)
            for _owner, _member_name, selector, line, end_line, is_entry_point, _return_type in self._iter_java_callable_metadata(
                result
            )
        ]

    def _get_java_selectors_for_member(
        self,
        file_path: str,
        owner_name: str,
        member_name: str,
    ) -> list[str]:
        """Return overload-aware selectors for a member on a given Java owner."""
        return list(
            self._java_member_selectors_by_class.get(
                f"{file_path}:{owner_name}", {}
            ).get(member_name, [])
        )

    def _get_java_file_local_member_matches(
        self,
        file_path: str,
        member_name: str,
        argument_types: list[str] | None = None,
    ) -> str | None:
        """Return a unique file-local Java member match for a bare method name."""
        matches: list[str] = []
        for class_key, member_map in self._java_member_selectors_by_class.items():
            if not class_key.startswith(f"{file_path}:"):
                continue
            matches.extend(member_map.get(member_name, []))
        selected = self._select_java_selector(sorted(matches), argument_types)
        return f"{file_path}:{selected}" if selected else None

    # [20260307_FEATURE] Track canonical Java type names for package/import resolution.
    def _iter_java_type_names(self, result) -> list[str]:
        """Return canonical Java type names from a parse result."""
        type_names: list[str] = []

        def add_class(class_info, prefix: str | None = None) -> None:
            qualified_class = (
                f"{prefix}.{class_info.name}" if prefix else class_info.name
            )
            type_names.append(qualified_class)

            for inner_class in getattr(class_info, "inner_classes", []) or []:
                add_class(inner_class, qualified_class)

            for inner_record in getattr(class_info, "inner_records", []) or []:
                add_record(inner_record, qualified_class)

            for inner_enum in getattr(class_info, "inner_enums", []) or []:
                add_enum(inner_enum, qualified_class)

        def add_record(record_info, prefix: str | None = None) -> None:
            qualified_record = (
                f"{prefix}.{record_info.name}" if prefix else record_info.name
            )
            type_names.append(qualified_record)

        def add_interface(interface_info, prefix: str | None = None) -> None:
            qualified_interface = (
                f"{prefix}.{interface_info.name}" if prefix else interface_info.name
            )
            type_names.append(qualified_interface)

        def add_enum(enum_info, prefix: str | None = None) -> None:
            qualified_enum = f"{prefix}.{enum_info.name}" if prefix else enum_info.name
            type_names.append(qualified_enum)

        for class_info in getattr(result, "classes", []) or []:
            add_class(class_info)

        for record_info in getattr(result, "records", []) or []:
            add_record(record_info)

        for interface_info in getattr(result, "interfaces", []) or []:
            add_interface(interface_info)

        for enum_info in getattr(result, "enums", []) or []:
            add_enum(enum_info)

        return type_names

    # [20260307_FEATURE] Resolve Java type references for Pro/Enterprise cross-file call graph edges.
    def _resolve_java_type_reference(
        self,
        current_file: str,
        type_name: str,
    ) -> tuple[str | None, str | None]:
        """Resolve a Java type reference to its defining file and fully-qualified name."""
        if not type_name:
            return None, None

        imports = self.imports.get(current_file, {})
        current_package = self._java_packages.get(current_file, "")
        candidates: list[str] = []
        seen: set[str] = set()

        def add_candidate(fqcn: str) -> None:
            if fqcn in self._java_types_by_fqcn and fqcn not in seen:
                seen.add(fqcn)
                candidates.append(fqcn)

        add_candidate(type_name)

        if "." in type_name:
            head, tail = type_name.split(".", 1)
            imported = imports.get(head)
            if imported:
                add_candidate(f"{imported}.{tail}")
            if current_package:
                add_candidate(f"{current_package}.{type_name}")
        else:
            imported = imports.get(type_name)
            if imported:
                add_candidate(imported)
            if current_package:
                add_candidate(f"{current_package}.{type_name}")
            for fqcn in sorted(self._java_simple_type_index.get(type_name, set())):
                add_candidate(fqcn)

        if len(candidates) != 1:
            return None, None

        fqcn = candidates[0]
        return self._java_types_by_fqcn.get(fqcn), fqcn

    # [20260307_FEATURE] Resolve Java static imports to canonical call graph nodes.
    def _resolve_java_static_import(
        self, current_file: str, member_name: str
    ) -> str | None:
        """Resolve a Java static import to a canonical call graph node."""
        return self._resolve_java_static_import_with_args(
            current_file, member_name, None
        )

    def _resolve_java_static_import_with_args(
        self,
        current_file: str,
        member_name: str,
        argument_types: list[str] | None,
    ) -> str | None:
        """Resolve a Java static import to a canonical call graph node with overload awareness."""
        for static_import in self._java_static_imports_raw.get(current_file, []):
            if static_import.endswith(".*"):
                type_fqcn = static_import[:-2]
                target_file = self._java_types_by_fqcn.get(type_fqcn)
                local_type = self._java_fqcn_to_local.get(type_fqcn)
                if not target_file or not local_type:
                    continue
                selector = self._select_java_selector(
                    self._get_java_selectors_for_member(
                        target_file, local_type, member_name
                    ),
                    argument_types,
                )
                if selector:
                    return f"{target_file}:{selector}"
                continue

            if "." not in static_import:
                continue

            type_fqcn, imported_member = static_import.rsplit(".", 1)
            if imported_member != member_name:
                continue

            target_file = self._java_types_by_fqcn.get(type_fqcn)
            local_type = self._java_fqcn_to_local.get(type_fqcn)
            if not target_file or not local_type:
                continue

            selector = self._select_java_selector(
                self._get_java_selectors_for_member(
                    target_file, local_type, member_name
                ),
                argument_types,
            )
            if selector:
                return f"{target_file}:{selector}"

        return None

    # [20260307_FEATURE] Resolve Java field-backed instance members for get_call_graph advanced resolution.
    def _resolve_java_field_type(
        self,
        current_file: str,
        current_class: str,
        field_name: str,
    ) -> str | None:
        """Resolve a field name to its declared Java type within a class hierarchy."""
        visited: set[str] = set()
        next_type: str | None = current_class

        while next_type and next_type not in visited:
            visited.add(next_type)
            class_key = f"{current_file}:{next_type}"
            field_types = self._java_field_types_by_class.get(class_key, {})
            if field_name in field_types:
                return field_types[field_name]

            _, next_fqcn = self._resolve_java_type_reference(current_file, next_type)
            if not next_fqcn:
                break
            next_type = self._java_superclass_refs.get(next_fqcn)

        return None

    # [20260307_FEATURE] Walk Java inheritance for get_call_graph advanced resolution.
    def _resolve_java_member_on_type(
        self,
        current_file: str,
        type_name: str,
        member_name: str,
        argument_types: list[str] | None = None,
    ) -> str | None:
        """Resolve a Java member on a type or one of its superclasses."""
        target_file: str | None
        target_fqcn: str | None

        if type_name in self._java_types_by_fqcn:
            target_fqcn = type_name
            target_file = self._java_types_by_fqcn.get(type_name)
        else:
            target_file, target_fqcn = self._resolve_java_type_reference(
                current_file,
                type_name,
            )

        visited: set[str] = set()
        while target_file and target_fqcn and target_fqcn not in visited:
            visited.add(target_fqcn)
            local_type = self._java_fqcn_to_local.get(target_fqcn)
            if local_type:
                selector = self._select_java_selector(
                    self._get_java_selectors_for_member(
                        target_file, local_type, member_name
                    ),
                    argument_types,
                )
                if selector:
                    return f"{target_file}:{selector}"

            superclass_ref = self._java_superclass_refs.get(target_fqcn)
            if not superclass_ref:
                break

            target_file, target_fqcn = self._resolve_java_type_reference(
                target_file,
                superclass_ref,
            )

        return None

    # [20260307_FEATURE] Populate Java definitions so get_call_graph can emit canonical Java nodes.
    def _analyze_definitions_java(self, file_path: Path, rel_path: str) -> None:
        """Extract Java class and callable definitions."""
        parser, result = self._load_java_parse_result(file_path)
        if parser is None or result is None:
            return

        self._collect_java_sam_interfaces(parser, parser._tree.root_node, rel_path)

        package_name = (getattr(result, "package", None) or "").strip()
        self._java_packages[rel_path] = package_name
        self._java_imports_raw[rel_path] = list(getattr(result, "imports", []) or [])
        self._java_static_imports_raw[rel_path] = list(
            getattr(result, "static_imports", []) or []
        )

        definitions: Set[str] = set()
        member_selectors_by_class: Dict[str, Dict[str, List[str]]] = {}

        def add_class(class_info, prefix: str | None = None) -> None:
            qualified_class = (
                f"{prefix}.{class_info.name}" if prefix else class_info.name
            )
            definitions.add(qualified_class)
            fqcn = (
                f"{package_name}.{qualified_class}" if package_name else qualified_class
            )
            if getattr(class_info, "superclass", None):
                self._java_superclass_refs[fqcn] = class_info.superclass
            self._java_field_types_by_class[f"{rel_path}:{qualified_class}"] = {
                field.name: field.field_type
                for field in getattr(class_info, "fields", []) or []
                if getattr(field, "name", None) and getattr(field, "field_type", None)
            }
            for inner_class in getattr(class_info, "inner_classes", []) or []:
                add_class(inner_class, qualified_class)
            for inner_record in getattr(class_info, "inner_records", []) or []:
                add_record(inner_record, qualified_class)
            for inner_enum in getattr(class_info, "inner_enums", []) or []:
                add_enum(inner_enum, qualified_class)

        def add_record(record_info, prefix: str | None = None) -> None:
            qualified_record = (
                f"{prefix}.{record_info.name}" if prefix else record_info.name
            )
            definitions.add(qualified_record)

        def add_interface(interface_info, prefix: str | None = None) -> None:
            qualified_interface = (
                f"{prefix}.{interface_info.name}" if prefix else interface_info.name
            )
            definitions.add(qualified_interface)

        def add_enum(enum_info, prefix: str | None = None) -> None:
            qualified_enum = f"{prefix}.{enum_info.name}" if prefix else enum_info.name
            definitions.add(qualified_enum)

        for class_info in getattr(result, "classes", []) or []:
            add_class(class_info)

        for record_info in getattr(result, "records", []) or []:
            add_record(record_info)

        for interface_info in getattr(result, "interfaces", []) or []:
            add_interface(interface_info)

        for enum_info in getattr(result, "enums", []) or []:
            add_enum(enum_info)

        for (
            owner_name,
            member_name,
            selector,
            _line,
            _end_line,
            _is_entry,
            return_type,
        ) in self._iter_java_callable_metadata(result):
            definitions.add(selector)
            member_selectors_by_class.setdefault(
                f"{rel_path}:{owner_name}", {}
            ).setdefault(member_name, []).append(selector)
            if return_type:
                self._java_selector_return_types[f"{rel_path}:{selector}"] = (
                    self._normalize_java_selector_type(return_type)
                )

        self.definitions[rel_path] = definitions
        self._java_member_selectors_by_class.update(member_selectors_by_class)
        self.imports[rel_path] = {
            imported_type.split(".")[-1]: imported_type
            for imported_type in self._java_imports_raw.get(rel_path, [])
            if imported_type
        }

        for local_type in self._iter_java_type_names(result):
            fqcn = f"{package_name}.{local_type}" if package_name else local_type
            self._java_types_by_fqcn[fqcn] = rel_path
            self._java_fqcn_to_local[fqcn] = local_type
            self._java_simple_type_index.setdefault(local_type, set()).add(fqcn)
            self._java_simple_type_index.setdefault(
                local_type.split(".")[-1], set()
            ).add(fqcn)

    # [20260307_FEATURE] Resolve minimal Java intra-file calls against canonical Class.method nodes.
    def _analyze_calls_java(
        self,
        file_path: Path,
        rel_path: str,
        advanced_resolution: bool = False,
    ) -> Dict[str, List[str]]:
        """Extract Java method calls and resolve canonical same-file or cross-file callees."""
        parser, result = self._load_java_parse_result(file_path)
        if parser is None or result is None or getattr(parser, "_tree", None) is None:
            return {}

        definitions = self.definitions.get(rel_path, set())
        file_graph: Dict[str, List[str]] = {}
        root = parser._tree.root_node

        java_type_node_types = {
            "type_identifier",
            "scoped_type_identifier",
            "generic_type",
            "array_type",
            "integral_type",
            "floating_point_type",
            "boolean_type",
        }

        def get_declared_type(node) -> str | None:
            for child in getattr(node, "children", []) or []:
                if child.type in java_type_node_types:
                    return parser._get_text(child)
            return None

        def collect_var_types(node) -> dict[str, str]:
            var_types: dict[str, str] = {}

            def visit(cur) -> None:
                if cur.type in {"formal_parameter", "spread_parameter"}:
                    declared_type = get_declared_type(cur)
                    name_node = parser._find_child_by_type(cur, "identifier")
                    if declared_type and name_node is not None:
                        var_types[parser._get_text(name_node)] = declared_type
                elif cur.type == "local_variable_declaration":
                    declared_type = get_declared_type(cur)
                    if declared_type:
                        for declarator in parser._find_children_by_type(
                            cur, "variable_declarator"
                        ):
                            name_node = parser._find_child_by_type(
                                declarator, "identifier"
                            )
                            if name_node is not None and declared_type != "var":
                                var_types[parser._get_text(name_node)] = declared_type

                for child in getattr(cur, "children", []) or []:
                    if getattr(child, "is_named", False):
                        visit(child)

            visit(node)
            return var_types

        def split_generic_arguments(argument_block: str) -> list[str]:
            generic_args: list[str] = []
            current: list[str] = []
            depth = 0
            for char in argument_block:
                if char == "<":
                    depth += 1
                elif char == ">":
                    depth = max(depth - 1, 0)
                elif char == "," and depth == 0:
                    generic_args.append("".join(current).strip())
                    current = []
                    continue
                current.append(char)
            if current:
                generic_args.append("".join(current).strip())
            return generic_args

        def parse_generic_type_signature(type_name: str) -> tuple[str, list[str]]:
            normalized_type = self._normalize_java_selector_type(type_name)
            if normalized_type in {"?", "null"}:
                return normalized_type, []

            generic_start = normalized_type.find("<")
            generic_end = normalized_type.rfind(">")
            if generic_start <= 0 or generic_end <= generic_start:
                return normalized_type, []

            base_type = normalized_type[:generic_start]
            generic_body = normalized_type[generic_start + 1 : generic_end]
            return base_type, split_generic_arguments(generic_body)

        def substitute_java_type_parameters(
            type_name: str,
            substitutions: dict[str, str],
        ) -> str:
            normalized_type = self._normalize_java_selector_type(type_name)
            if normalized_type in substitutions:
                return self._normalize_java_selector_type(
                    substitutions[normalized_type]
                )
            if not substitutions:
                return normalized_type
            for placeholder, concrete_type in substitutions.items():
                normalized_type = re.sub(
                    rf"\b{re.escape(placeholder)}\b",
                    self._normalize_java_selector_type(concrete_type),
                    normalized_type,
                )
            return normalized_type

        # [20260309_FEATURE] Recover Java functional-interface signatures from declared generics so lambda bodies and method references stay selector-aware in the shared runtime.
        def infer_functional_interface_signature(
            functional_type: str,
            method_name: str | None = None,
        ) -> tuple[list[str], str]:
            base_type, generic_args = parse_generic_type_signature(functional_type)
            if base_type in {"?", "null"}:
                return [], "?"

            signature_by_type = {
                "Supplier": ([], 0),
                "Callable": ([], 0),
                "Function": ([0], -1),
                "BiFunction": ([0, 1], -1),
                "UnaryOperator": ([0], 0),
                "BinaryOperator": ([0, 0], 0),
                "Predicate": ([0], "boolean"),
                "BiPredicate": ([0, 1], "boolean"),
                "Consumer": ([0], "void"),
                "BiConsumer": ([0, 1], "void"),
                "Runnable": ([], "void"),
            }
            param_indexes, return_spec = signature_by_type.get(base_type, ([], "?"))

            if base_type not in signature_by_type:

                def resolve_project_sam_signature(
                    target_file: str,
                    local_type: str,
                    concrete_args: list[str],
                    visited: set[str],
                ) -> tuple[list[str], str] | None:
                    interface_key = f"{target_file}:{local_type}"
                    if interface_key in visited:
                        return None
                    visited.add(interface_key)

                    type_parameters, extends_interfaces = (
                        self._java_interface_extends.get(
                            interface_key,
                            ([], []),
                        )
                    )
                    substitutions = {
                        type_param: generic_arg
                        for type_param, generic_arg in zip(
                            type_parameters, concrete_args
                        )
                    }

                    sam_signature = self._java_sam_interfaces.get(interface_key)
                    if sam_signature is not None:
                        (
                            _sam_type_parameters,
                            sam_method_name,
                            sam_parameter_types,
                            sam_return_type,
                        ) = sam_signature
                        if method_name is not None and sam_method_name != method_name:
                            return None
                        return (
                            [
                                substitute_java_type_parameters(
                                    param_type, substitutions
                                )
                                for param_type in sam_parameter_types
                            ],
                            substitute_java_type_parameters(
                                sam_return_type, substitutions
                            ),
                        )

                    for extends_interface in extends_interfaces:
                        extends_base, extends_args = parse_generic_type_signature(
                            extends_interface
                        )
                        resolved_file, resolved_fqcn = (
                            self._resolve_java_type_reference(
                                target_file,
                                extends_base,
                            )
                        )
                        resolved_local_type = (
                            self._java_fqcn_to_local.get(resolved_fqcn)
                            if resolved_fqcn
                            else None
                        )
                        if not resolved_file or not resolved_local_type:
                            continue
                        substituted_args = [
                            substitute_java_type_parameters(arg, substitutions)
                            for arg in extends_args
                        ]
                        resolved_signature = resolve_project_sam_signature(
                            resolved_file,
                            resolved_local_type,
                            substituted_args,
                            visited,
                        )
                        if resolved_signature is not None:
                            return resolved_signature

                    return None

                target_file, target_fqcn = self._resolve_java_type_reference(
                    rel_path,
                    base_type,
                )
                local_type = (
                    self._java_fqcn_to_local.get(target_fqcn) if target_fqcn else None
                )
                if target_file and local_type:
                    resolved_signature = resolve_project_sam_signature(
                        target_file,
                        local_type,
                        generic_args,
                        set(),
                    )
                    if resolved_signature is not None:
                        return resolved_signature

            parameter_types: list[str] = []
            for index in param_indexes:
                if 0 <= index < len(generic_args):
                    parameter_types.append(
                        self._normalize_java_selector_type(generic_args[index])
                    )
                else:
                    parameter_types.append("?")

            if isinstance(return_spec, str):
                return_type = return_spec
            elif generic_args:
                resolved_index = (
                    return_spec if return_spec >= 0 else len(generic_args) + return_spec
                )
                if 0 <= resolved_index < len(generic_args):
                    return_type = self._normalize_java_selector_type(
                        generic_args[resolved_index]
                    )
                else:
                    return_type = "?"
            else:
                return_type = "?"

            if method_name is not None:
                expected_method = {
                    "Supplier": "get",
                    "Callable": "call",
                    "Function": "apply",
                    "BiFunction": "apply",
                    "UnaryOperator": "apply",
                    "BinaryOperator": "apply",
                    "Predicate": "test",
                    "BiPredicate": "test",
                    "Consumer": "accept",
                    "BiConsumer": "accept",
                    "Runnable": "run",
                }.get(base_type)
                if expected_method is not None and method_name != expected_method:
                    return [], "?"

            return parameter_types, return_type

        def infer_functional_interface_return_type(
            receiver_type: str,
            method_name: str,
        ) -> str:
            return infer_functional_interface_signature(receiver_type, method_name)[1]

        def get_lambda_parameter_names(node) -> list[str]:
            named_children = [
                child
                for child in (getattr(node, "children", []) or [])
                if getattr(child, "is_named", False)
            ]
            if not named_children:
                return []

            first_child = named_children[0]
            if first_child.type in {"formal_parameters", "inferred_parameters"}:
                parameter_names: list[str] = []
                for parameter_node in getattr(first_child, "children", []) or []:
                    if not getattr(parameter_node, "is_named", False):
                        continue
                    if parameter_node.type in {
                        "formal_parameter",
                        "spread_parameter",
                        "receiver_parameter",
                    }:
                        name_node = parameter_node.child_by_field_name("name")
                        if name_node is not None:
                            parameter_names.append(parser._get_text(name_node))
                    elif parameter_node.type == "identifier":
                        parameter_names.append(parser._get_text(parameter_node))
                return parameter_names

            if first_child.type == "identifier":
                parameter_names: list[str] = []
                for child in named_children[:-1]:
                    if getattr(child, "type", "") != "identifier":
                        break
                    parameter_names.append(parser._get_text(child))
                return parameter_names or [parser._get_text(first_child)]

            return []

        def get_enclosing_functional_type(node) -> str | None:
            parent = getattr(node, "parent", None)
            while parent is not None:
                if parent.type == "local_variable_declaration":
                    return get_declared_type(parent)
                parent = getattr(parent, "parent", None)
            return None

        # [20260308_FEATURE] Infer Java expression types for casts and chained receivers so overload resolution can use the same shared selector runtime.
        def infer_expression_type(
            node,
            current_class: str,
            var_types: dict[str, str],
        ) -> str:
            if node is None:
                return "?"

            node_text = parser._get_text(node).strip()
            node_type = getattr(node, "type", "")

            if node_type in {
                "decimal_integer_literal",
                "hex_integer_literal",
                "octal_integer_literal",
                "binary_integer_literal",
            }:
                return "int"
            if node_type in {
                "decimal_floating_point_literal",
                "hex_floating_point_literal",
            }:
                return "double"
            if node_type == "string_literal":
                return "String"
            if node_type == "character_literal":
                return "char"
            if node_text in {"true", "false"}:
                return "boolean"
            if node_text == "null":
                return "null"

            if node_type == "identifier":
                return self._normalize_java_selector_type(
                    var_types.get(node_text)
                    or self._resolve_java_field_type(
                        rel_path,
                        current_class,
                        node_text,
                    )
                    or "?"
                )

            if node_type == "field_access":
                object_node = node.child_by_field_name("object")
                field_node = node.child_by_field_name("field")
                field_name = parser._get_text(field_node) if field_node else ""
                receiver_text = (
                    parser._get_text(object_node).strip() if object_node else ""
                )
                if receiver_text in {"this", "super"}:
                    return self._normalize_java_selector_type(
                        self._resolve_java_field_type(
                            rel_path,
                            current_class,
                            field_name,
                        )
                        or "?"
                    )
                if receiver_text in var_types and field_name:
                    field_owner_type = var_types[receiver_text]
                    resolved_field_type = self._resolve_java_field_type(
                        rel_path,
                        field_owner_type,
                        field_name,
                    )
                    if resolved_field_type:
                        return self._normalize_java_selector_type(resolved_field_type)
                return self._normalize_java_selector_type(
                    self._resolve_java_field_type(
                        rel_path,
                        current_class,
                        field_name,
                    )
                    or "?"
                )

            if node_type == "object_creation_expression":
                type_node = node.child_by_field_name("type")
                return self._normalize_java_selector_type(
                    parser._get_text(type_node) if type_node else "?"
                )

            if node_type == "parenthesized_expression":
                for child in getattr(node, "children", []) or []:
                    if getattr(child, "is_named", False):
                        return infer_expression_type(child, current_class, var_types)
                return "?"

            if node_type == "cast_expression":
                for child in getattr(node, "children", []) or []:
                    if getattr(child, "type", "") in java_type_node_types:
                        return self._normalize_java_selector_type(
                            parser._get_text(child)
                        )
                return "?"

            if node_type == "method_invocation":
                resolved_callee = resolve_method_invocation(
                    node, current_class, var_types
                )
                return_type = self._java_selector_return_types.get(resolved_callee, "?")
                if return_type != "?":
                    return return_type

                object_node = node.child_by_field_name("object")
                name_node = node.child_by_field_name("name")
                method_name = parser._get_text(name_node) if name_node else ""
                if object_node is not None and method_name:
                    receiver_type = infer_expression_type(
                        object_node,
                        current_class,
                        var_types,
                    )
                    functional_return_type = infer_functional_interface_return_type(
                        receiver_type,
                        method_name,
                    )
                    if functional_return_type != "?":
                        return functional_return_type
                return "?"

            return "?"

        def infer_argument_types(
            node, current_class: str, var_types: dict[str, str]
        ) -> list[str]:
            argument_list = parser._find_child_by_type(node, "argument_list")
            if argument_list is None:
                return []

            inferred_types: list[str] = []
            for child in getattr(argument_list, "children", []) or []:
                if not getattr(child, "is_named", False):
                    continue
                inferred_types.append(
                    infer_expression_type(child, current_class, var_types)
                )

            return inferred_types

        def update_var_types_from_node(
            node,
            current_class: str,
            var_types: dict[str, str],
        ) -> None:
            if node.type == "local_variable_declaration":
                declared_type = get_declared_type(node)
                for declarator in parser._find_children_by_type(
                    node, "variable_declarator"
                ):
                    name_node = declarator.child_by_field_name("name")
                    value_node = declarator.child_by_field_name("value")
                    if name_node is None:
                        continue
                    var_name = parser._get_text(name_node)
                    if declared_type and declared_type != "var":
                        var_types[var_name] = declared_type
                        continue
                    if value_node is not None:
                        inferred_type = infer_expression_type(
                            value_node,
                            current_class,
                            var_types,
                        )
                        if inferred_type not in {"?", "null"}:
                            var_types[var_name] = inferred_type
                return

            if node.type == "assignment_expression":
                left_node = node.child_by_field_name("left")
                right_node = node.child_by_field_name("right")
                if (
                    left_node is None
                    or right_node is None
                    or left_node.type != "identifier"
                ):
                    return
                inferred_type = infer_expression_type(
                    right_node,
                    current_class,
                    var_types,
                )
                if inferred_type not in {"?", "null"}:
                    var_types[parser._get_text(left_node)] = inferred_type

        selector_by_line: Dict[tuple[str, int, bool], str] = {}
        for (
            owner_name,
            member_name,
            selector,
            line,
            _end_line,
            _is_entry,
            _return_type,
        ) in self._iter_java_callable_metadata(result):
            is_constructor = member_name == owner_name.split(".")[-1]
            selector_by_line[(owner_name, line, is_constructor)] = selector

        def resolve_callee(
            raw_callee: str,
            current_class: str,
            var_types: dict[str, str],
            argument_types: list[str] | None = None,
        ) -> str:
            if not raw_callee:
                return raw_callee

            if raw_callee.startswith("this."):
                method_name = raw_callee.split(".", 1)[1]
                selector = self._select_java_selector(
                    self._get_java_selectors_for_member(
                        rel_path, current_class, method_name
                    ),
                    argument_types,
                )
                if selector:
                    return f"{rel_path}:{selector}"
                if advanced_resolution:
                    inherited = self._resolve_java_member_on_type(
                        rel_path,
                        current_class,
                        method_name,
                        argument_types,
                    )
                    if inherited:
                        return inherited

            if "." not in raw_callee:
                local_selector = self._select_java_selector(
                    self._get_java_selectors_for_member(
                        rel_path, current_class, raw_callee
                    ),
                    argument_types,
                )
                if local_selector:
                    return f"{rel_path}:{local_selector}"

                constructor_selector = self._select_java_selector(
                    self._get_java_selectors_for_member(
                        rel_path, raw_callee, raw_callee
                    ),
                    argument_types,
                )
                if constructor_selector:
                    return f"{rel_path}:{constructor_selector}"

                if raw_callee in definitions:
                    return f"{rel_path}:{raw_callee}"

                suffix_match = self._get_java_file_local_member_matches(
                    rel_path,
                    raw_callee,
                    argument_types,
                )
                if suffix_match:
                    return suffix_match

                if advanced_resolution:
                    inherited = self._resolve_java_member_on_type(
                        rel_path,
                        current_class,
                        raw_callee,
                        argument_types,
                    )
                    if inherited:
                        return inherited

                    static_target = self._resolve_java_static_import_with_args(
                        rel_path,
                        raw_callee,
                        argument_types,
                    )
                    if static_target:
                        return static_target

                    target_file, target_fqcn = self._resolve_java_type_reference(
                        rel_path,
                        raw_callee,
                    )
                    local_type = (
                        self._java_fqcn_to_local.get(target_fqcn)
                        if target_fqcn
                        else None
                    )
                    if target_file and local_type:
                        constructor_selector = self._select_java_selector(
                            self._get_java_selectors_for_member(
                                target_file,
                                local_type,
                                local_type.split(".")[-1],
                            ),
                            argument_types,
                        )
                        if constructor_selector:
                            return f"{target_file}:{constructor_selector}"

                return raw_callee

            receiver, member = raw_callee.rsplit(".", 1)
            if receiver == "this":
                selector = self._select_java_selector(
                    self._get_java_selectors_for_member(
                        rel_path, current_class, member
                    ),
                    argument_types,
                )
                if selector:
                    return f"{rel_path}:{selector}"
                if advanced_resolution:
                    inherited = self._resolve_java_member_on_type(
                        rel_path,
                        current_class,
                        member,
                        argument_types,
                    )
                    if inherited:
                        return inherited

            if receiver.startswith("this.") and advanced_resolution:
                field_name = receiver.split(".", 1)[1]
                field_type = self._resolve_java_field_type(
                    rel_path,
                    current_class,
                    field_name,
                )
                if field_type:
                    inferred = self._resolve_java_member_on_type(
                        rel_path,
                        field_type,
                        member,
                        argument_types,
                    )
                    if inferred:
                        return inferred

            if receiver == "super" and advanced_resolution:
                inherited = self._resolve_java_member_on_type(
                    rel_path,
                    current_class,
                    member,
                    argument_types,
                )
                if inherited:
                    return inherited

            selector = self._select_java_selector(
                self._get_java_selectors_for_member(rel_path, receiver, member),
                argument_types,
            )
            if selector:
                return f"{rel_path}:{selector}"

            if advanced_resolution:
                if receiver in var_types:
                    inferred = self._resolve_java_member_on_type(
                        rel_path,
                        var_types[receiver],
                        member,
                        argument_types,
                    )
                    if inferred:
                        return inferred

                field_type = self._resolve_java_field_type(
                    rel_path,
                    current_class,
                    receiver,
                )
                if field_type:
                    inferred = self._resolve_java_member_on_type(
                        rel_path,
                        field_type,
                        member,
                        argument_types,
                    )
                    if inferred:
                        return inferred

                target_file, target_fqcn = self._resolve_java_type_reference(
                    rel_path,
                    receiver,
                )
                local_type = (
                    self._java_fqcn_to_local.get(target_fqcn) if target_fqcn else None
                )
                if target_file and local_type:
                    selector = self._select_java_selector(
                        self._get_java_selectors_for_member(
                            target_file, local_type, member
                        ),
                        argument_types,
                    )
                    if selector:
                        return f"{target_file}:{selector}"

            return raw_callee

        def resolve_method_invocation(
            node,
            current_class: str,
            var_types: dict[str, str],
        ) -> str:
            name_node = node.child_by_field_name("name")
            object_node = node.child_by_field_name("object")
            method_name = parser._get_text(name_node) if name_node else ""
            receiver = parser._get_text(object_node) if object_node else ""
            raw_callee = f"{receiver}.{method_name}" if receiver else method_name
            argument_types = infer_argument_types(node, current_class, var_types)

            if advanced_resolution and object_node is not None and method_name:
                receiver_type = infer_expression_type(
                    object_node,
                    current_class,
                    var_types,
                )
                if receiver_type not in {"?", "null"}:
                    inferred = self._resolve_java_member_on_type(
                        rel_path,
                        receiver_type,
                        method_name,
                        argument_types,
                    )
                    if inferred:
                        return inferred

            return resolve_callee(
                raw_callee,
                current_class,
                var_types,
                argument_types,
            )

        def resolve_constructor_invocation(
            node,
            current_class: str,
            var_types: dict[str, str],
        ) -> str:
            invocation_text = parser._get_text(node).strip()
            argument_types = infer_argument_types(node, current_class, var_types)

            if invocation_text.startswith("this"):
                selector = self._select_java_selector(
                    self._get_java_selectors_for_member(
                        rel_path,
                        current_class,
                        current_class.split(".")[-1],
                    ),
                    argument_types,
                )
                if selector:
                    return f"{rel_path}:{selector}"
                return invocation_text

            if invocation_text.startswith("super") and advanced_resolution:
                package_name = self._java_packages.get(rel_path, "")
                current_fqcn = (
                    f"{package_name}.{current_class}" if package_name else current_class
                )
                superclass_ref = self._java_superclass_refs.get(current_fqcn)
                if superclass_ref:
                    target_file, target_fqcn = self._resolve_java_type_reference(
                        rel_path,
                        superclass_ref,
                    )
                    local_type = (
                        self._java_fqcn_to_local.get(target_fqcn)
                        if target_fqcn
                        else None
                    )
                    if target_file and local_type:
                        selector = self._select_java_selector(
                            self._get_java_selectors_for_member(
                                target_file,
                                local_type,
                                local_type.split(".")[-1],
                            ),
                            argument_types,
                        )
                        if selector:
                            return f"{target_file}:{selector}"

            return invocation_text

        # [20260309_FEATURE] Resolve simple Java method references so this::method and Type::method contribute concrete graph edges.
        def resolve_method_reference(
            node,
            current_class: str,
            var_types: dict[str, str],
            expected_argument_types: list[str] | None = None,
        ) -> str:
            node_text = parser._get_text(node).strip()
            if "::" not in node_text:
                return parser._get_text(node).strip()
            receiver_text, member_name = [
                part.strip() for part in node_text.split("::", 1)
            ]

            if not receiver_text or not member_name:
                return parser._get_text(node).strip()

            if member_name == "new":
                constructor_target = self._resolve_java_member_on_type(
                    rel_path,
                    receiver_text,
                    receiver_text.split(".")[-1],
                    expected_argument_types or [],
                )
                if constructor_target:
                    return constructor_target
                return resolve_callee(
                    receiver_text,
                    current_class,
                    var_types,
                    expected_argument_types or [],
                )

            if receiver_text in {"this", "super"}:
                return resolve_callee(
                    f"{receiver_text}.{member_name}",
                    current_class,
                    var_types,
                    expected_argument_types or [],
                )

            receiver_type = self._normalize_java_selector_type(
                var_types.get(receiver_text) or receiver_text
            )
            if advanced_resolution and receiver_type not in {"?", "null"}:
                inferred = self._resolve_java_member_on_type(
                    rel_path,
                    receiver_type,
                    member_name,
                    expected_argument_types or [],
                )
                if inferred:
                    return inferred

            return resolve_callee(
                f"{receiver_text}.{member_name}",
                current_class,
                var_types,
                expected_argument_types or [],
            )

        def collect_calls(
            node,
            current_class: str,
            calls: list[str],
            var_types: dict[str, str],
        ) -> None:
            update_var_types_from_node(node, current_class, var_types)

            if node.type == "method_invocation":
                resolved_callee = resolve_method_invocation(
                    node,
                    current_class,
                    var_types,
                )
                if resolved_callee:
                    calls.append(resolved_callee)
            elif node.type == "object_creation_expression":
                type_node = node.child_by_field_name("type")
                raw_callee = parser._get_text(type_node) if type_node else ""
                if raw_callee:
                    calls.append(
                        resolve_callee(
                            raw_callee,
                            current_class,
                            var_types,
                            infer_argument_types(node, current_class, var_types),
                        )
                    )
            elif node.type == "explicit_constructor_invocation":
                resolved_callee = resolve_constructor_invocation(
                    node,
                    current_class,
                    var_types,
                )
                if resolved_callee:
                    calls.append(resolved_callee)
            elif node.type == "lambda_expression":
                functional_type = get_enclosing_functional_type(node)
                lambda_parameter_types, _lambda_return_type = (
                    infer_functional_interface_signature(functional_type or "?")
                )
                lambda_var_types = dict(var_types)
                for parameter_name, parameter_type in zip(
                    get_lambda_parameter_names(node),
                    lambda_parameter_types,
                ):
                    if parameter_type not in {"?", "null"}:
                        lambda_var_types[parameter_name] = parameter_type
                named_children = [
                    child
                    for child in (getattr(node, "children", []) or [])
                    if getattr(child, "is_named", False)
                ]
                if named_children:
                    body_node = named_children[-1]
                    collect_calls(body_node, current_class, calls, lambda_var_types)
                return
            elif node.type == "method_reference":
                functional_type = get_enclosing_functional_type(node)
                expected_argument_types, _return_type = (
                    infer_functional_interface_signature(functional_type or "?")
                )
                resolved_callee = resolve_method_reference(
                    node,
                    current_class,
                    var_types,
                    expected_argument_types,
                )
                if resolved_callee:
                    calls.append(resolved_callee)
                return

            for child in getattr(node, "children", []) or []:
                if getattr(child, "is_named", False):
                    collect_calls(child, current_class, calls, var_types)

        def process_type(type_node, prefix: str | None = None) -> None:
            name_node = type_node.child_by_field_name("name")
            type_name = parser._get_text(name_node) if name_node else ""
            if not type_name:
                return

            qualified_type = f"{prefix}.{type_name}" if prefix else type_name
            body_node = parser._find_child_by_type(type_node, "class_body")
            if body_node is None and type_node.type == "record_declaration":
                body_node = parser._find_child_by_type(type_node, "record_body")
            if body_node is None:
                return

            for child in body_node.children:
                if child.type == "method_declaration":
                    method_name = parser._get_text(child.child_by_field_name("name"))
                    if not method_name:
                        continue
                    caller_selector = selector_by_line.get(
                        (qualified_type, parser._get_line(child), False),
                        f"{qualified_type}.{method_name}",
                    )
                    caller_key = f"{rel_path}:{caller_selector}"
                    calls: list[str] = []
                    var_types = collect_var_types(child)
                    collect_calls(child, qualified_type, calls, var_types)
                    file_graph[caller_key] = calls
                elif child.type in {
                    "constructor_declaration",
                    "compact_constructor_declaration",
                }:
                    caller_selector = selector_by_line.get(
                        (qualified_type, parser._get_line(child), True),
                        f"{qualified_type}.{type_name}",
                    )
                    caller_key = f"{rel_path}:{caller_selector}"
                    calls: list[str] = []
                    var_types = collect_var_types(child)
                    collect_calls(child, qualified_type, calls, var_types)
                    file_graph[caller_key] = calls
                elif child.type in {"class_declaration", "record_declaration"}:
                    process_type(child, qualified_type)

        for child in root.children:
            if child.type in {"class_declaration", "record_declaration"}:
                process_type(child)

        return file_graph

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
                        imported = getattr(
                            getattr(spec, "imported", None), "name", None
                        )
                        local = (
                            getattr(getattr(spec, "local", None), "name", None)
                            or imported
                        )
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
        if not module_spec:
            return None

        if not module_spec.startswith("."):
            if self._js_ts_alias_resolver is None:
                return None
            try:
                resolved_file = self._js_ts_alias_resolver.resolve_to_file(module_spec)
            except Exception:
                resolved_file = None
            if resolved_file is None:
                return None
            try:
                if resolved_file.exists() and resolved_file.is_file():
                    return str(resolved_file.relative_to(self.root_path)).replace("\\", "/")
            except Exception:
                return None
            return None

        base_dir = (self.root_path / from_file).parent
        # Handle './x', './x.js', './x.ts', './x/index.js', etc.
        candidate_bases = [module_spec]
        if not any(
            module_spec.endswith(ext)
            for ext in (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")
        ):
            candidate_bases.extend(
                [
                    module_spec + ext
                    for ext in (".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs")
                ]
            )

        candidates: list[Path] = []
        for base in candidate_bases:
            candidates.append((base_dir / base).resolve())
        # index.* fallback
        if module_spec and not module_spec.endswith(
            (".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs")
        ):
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
    ) -> Dict[str, List[str]]:
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
                    callable_ranges.append(
                        (sym.line, end_line, sym.name, sym.parent_name)
                    )

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
            file_graph: Dict[str, List[str]] = {}

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
                                file_graph.setdefault(caller_key, []).append(
                                    _resolve_callee(raw, caller_parent)
                                )

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

        file_graph: Dict[str, List[str]] = {}

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

            if isinstance(
                cur, (esprima.nodes.CallExpression, esprima.nodes.NewExpression)
            ):
                raw = _callee_name(cur)
                if raw and current_fn not in {"<global>", "<anonymous>", "<arrow>"}:
                    caller_key = f"{rel_path}:{current_fn}"
                    file_graph.setdefault(caller_key, []).append(
                        _resolve_callee(raw, None)
                    )

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
    ) -> Dict[str, List[str]]:
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
                self._var_types: Dict[str, str] = {}

            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                if not self._advanced_resolution:
                    self.generic_visit(node)
                    return

                old_class = self._current_class
                self._current_class = node.name
                self.generic_visit(node)
                self._current_class = old_class

            def visit_FunctionDef(
                self, node: ast.FunctionDef | ast.AsyncFunctionDef
            ) -> None:
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
        entry_point: Optional[str] = None,
        depth: int = 10,
        max_nodes: Optional[int] = None,
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
        node_info: Dict[str, CallNode] = {}

        # Python nodes
        for file_path in self._iter_source_files():
            rel_path = str(file_path.relative_to(self.root_path))
            suffix = file_path.suffix.lower()
            if suffix != ".py":
                continue
            try:
                with open(file_path, "r", encoding="utf-8") as f:
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
                                is_entry_point=self._is_entry_point(
                                    top, tree, rel_path=rel_path
                                ),
                            )
                        elif isinstance(top, ast.ClassDef):
                            for item in top.body:
                                if isinstance(
                                    item, (ast.FunctionDef, ast.AsyncFunctionDef)
                                ):
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
                                is_entry_point=self._is_entry_point(
                                    node, tree, rel_path=rel_path
                                ),
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
            top_level_called: Set[str] = set()
            call_stack: list[tuple[esprima.nodes.Node, str]] = [(ast_js, "<global>")]
            while call_stack:
                cur, current_fn = call_stack.pop()
                if isinstance(cur, esprima.nodes.FunctionDeclaration):
                    name = (
                        getattr(getattr(cur, "id", None), "name", None) or "<anonymous>"
                    )
                    for ch in _children(cur):
                        call_stack.append((ch, name))
                    continue

                if current_fn == "<global>" and isinstance(
                    cur, esprima.nodes.CallExpression
                ):
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
                top_level_called: Set[str] = set()
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
                    elif (
                        sym.kind == "method" and sym.parent_name and advanced_resolution
                    ):
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

        # [20260307_FEATURE] Emit canonical Java callable nodes so builder-level Java slices are observable.
        for file_path in self._iter_source_files():
            rel_path = str(file_path.relative_to(self.root_path))
            suffix = file_path.suffix.lower()
            if suffix != ".java":
                continue

            _, java_result = self._load_java_parse_result(file_path)
            if java_result is None:
                continue

            for (
                callable_name,
                line,
                end_line,
                is_entry_point,
            ) in self._iter_java_callable_details(java_result):
                key = f"{rel_path}:{callable_name}"
                node_info[key] = CallNode(
                    name=callable_name,
                    file=rel_path,
                    line=line,
                    end_line=end_line,
                    is_entry_point=is_entry_point,
                )

        # [20260307_FEATURE] Emit generic IR-backed callable nodes for the broader
        # normalizer-backed polyglot language set.
        for file_path in self._iter_source_files():
            rel_path = str(file_path.relative_to(self.root_path))
            suffix = file_path.suffix.lower()
            if suffix not in self._GENERIC_IR_EXTENSION_LANGUAGE_MAP:
                continue

            module = self._load_ir_module(file_path, rel_path)
            if module is None:
                continue

            for (
                callable_name,
                line,
                end_line,
                is_entry_point,
            ) in self._iter_ir_callable_details(module):
                key = f"{rel_path}:{callable_name}"
                node_info[key] = CallNode(
                    name=callable_name,
                    file=rel_path,
                    line=line,
                    end_line=end_line,
                    is_entry_point=is_entry_point,
                )

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

        nodes: List[CallNode] = []
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
        edges_full: List[CallEdge] = []
        edges: List[CallEdge] = []
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
            if (
                filename.startswith("test_")
                or "/tests" in filename
                or "/test_" in filename
            ):
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
                        if isinstance(inner, ast.Call) and isinstance(
                            inner.func, ast.Name
                        ):
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
        graph: Dict[str, List[str]],
        entry_point: str,
        max_depth: int,
    ) -> Set[str]:
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
                short_name = key.rsplit(":", 1)[-1]
                if key.endswith(f":{entry_point}") or short_name.endswith(
                    f".{entry_point}"
                ):
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
        nodes: List[CallNode],
        edges: List[CallEdge],
        entry_point: Optional[str],
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
        node_ids: Dict[str, str] = {}
        for i, node in enumerate(nodes):
            full_name = (
                f"{node.file}:{node.name}" if node.file != "<external>" else node.name
            )
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
            if node.is_entry_point or (
                entry_point and entry_point.endswith(f":{node.name}")
            ):
                lines.append(f'    {node_id}[["{label}"]]')  # Stadium shape for entry
            elif node.file == "<external>":
                lines.append(f"    {node_id}({label})")  # Round for external
            else:
                lines.append(f'    {node_id}["{label}"]')  # Rectangle for internal

        # Add edges
        for edge in edges:
            caller_id = node_ids.get(edge.caller) or node_ids.get(
                edge.caller.split(":")[-1]
            )
            callee_id = node_ids.get(edge.callee) or node_ids.get(
                edge.callee.split(":")[-1]
            )

            if caller_id and callee_id:
                lines.append(f"    {caller_id} --> {callee_id}")

        return "\n".join(lines)

    def detect_circular_imports(self) -> List[List[str]]:
        """
        Detect circular import cycles in the project.

        [20251213_FEATURE] P1 - Circular dependency detection

        Returns:
            List of cycles, where each cycle is a list of module paths
            e.g., [["a.py", "b.py", "a.py"], ["c.py", "d.py", "e.py", "c.py"]]
        """

        # Build import graph: module -> modules it imports
        import_graph: Dict[str, Set[str]] = {}

        for file_path in self._iter_source_files():
            rel_path = str(file_path.relative_to(self.root_path))
            suffix = file_path.suffix.lower()
            try:
                if suffix == ".py":
                    with open(file_path, "r", encoding="utf-8") as f:
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
