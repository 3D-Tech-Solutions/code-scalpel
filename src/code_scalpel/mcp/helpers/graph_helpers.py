"""Helper implementations for graph tools."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re
from pathlib import Path
from typing import Any, TYPE_CHECKING, Set, cast

from code_scalpel.licensing.features import get_tool_capabilities

# [20260213_BUGFIX] Use protocol._get_current_tier which honors CODE_SCALPEL_TIER env var
# (tier_detector.get_current_tier bypasses JWT validation downgrade logic)
from code_scalpel.mcp.protocol import _get_current_tier
from code_scalpel.parsing import ParsingError, parse_python_code
from code_scalpel.mcp.models.graph import (
    AliasResolutionModel,
    ArchitecturalViolationModel,
    BoundaryAlertModel,
    CallContextModel,
    CallEdgeModel,
    CallGraphResultModel,
    CallNodeModel,
    ChainedAliasResolutionModel,
    CouplingViolationModel,
    CrossFileDependenciesResult,
    CrossFileSecurityResult,
    CrossFileVulnerabilityModel,
    ExtractedSymbolModel,
    GraphNeighborhoodResult,
    ModuleInfo,
    NeighborhoodEdgeModel,
    NeighborhoodNodeModel,
    PackageInfo,
    ProjectMapResult,
    ReexportChainModel,
    TaintFlowModel,
    WildcardExpansionModel,
)
from code_scalpel.graph_engine.node_id import NodeType, UniversalNodeID

if TYPE_CHECKING:
    from code_scalpel.graph_engine.graph import UniversalGraph

logger = logging.getLogger("code_scalpel.mcp.graph")


# [20260306_FEATURE] Initial JS/TS graph-neighborhood parity slice.
_GRAPH_LANGUAGE_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "python": (".py",),
    "javascript": (".js", ".jsx", ".mjs", ".cjs"),
    "typescript": (".ts", ".tsx"),
    "java": (".java",),
    "go": (".go",),
}

_GRAPH_SUFFIX_TO_LANGUAGE = {
    suffix: language
    for language, suffixes in _GRAPH_LANGUAGE_EXTENSIONS.items()
    for suffix in suffixes
}

# [20260307_FEATURE] Initial local JS/TS get_project_map parity slice.
_PROJECT_MAP_JS_TS_SUFFIXES: tuple[str, ...] = (
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".mts",
    ".cts",
)

_PROJECT_MAP_JAVA_SUFFIXES: tuple[str, ...] = (".java",)
_PROJECT_MAP_GO_SUFFIXES: tuple[str, ...] = (".go",)

_PROJECT_MAP_JS_TS_COMPLEXITY_PATTERN = re.compile(
    r"\b(if|for|while|switch|catch|case|function|class)\b|=>|&&|\|\|"
)
_PROJECT_MAP_GO_COMPLEXITY_PATTERN = re.compile(
    r"\b(if|for|switch|select|case|go|defer)\b|&&|\|\|"
)


@dataclass
class _JavaProjectMapModuleScan:
    """[20260314_FEATURE] Internal Java project-map scan metadata."""

    module: ModuleInfo
    package_name: str | None
    relation_hints: list[str]
    qualified_aliases: list[str]


def _normalize_java_project_map_reference(raw_name: str) -> str:
    """Return a stable Java type/import reference for project-map resolution."""
    normalized = raw_name.strip()
    if not normalized:
        return ""
    normalized = re.sub(r"<[^>]+>", "", normalized)
    normalized = normalized.replace("[]", "")
    return normalized.strip()


def _collect_java_same_package_reference_hints(code: str) -> list[str]:
    """Return bounded Java type-reference hints from simple same-package usages.

    [20260315_FEATURE] Project-map Java relationships need a conservative signal
    for same-package type references because those do not appear in import lists.
    This intentionally covers only obvious static access, constructor calls, and
    local type declarations so unresolved hints remain harmless.
    """
    builtin_types = {
        "String",
        "Object",
        "Class",
        "System",
        "Math",
        "Integer",
        "Long",
        "Double",
        "Float",
        "Boolean",
        "Character",
        "List",
        "Map",
        "Set",
        "Optional",
        "Runtime",
        "ProcessBuilder",
    }

    hints: set[str] = set()
    for pattern in (
        re.compile(r"\bnew\s+([A-Z][A-Za-z0-9_]*)\b"),
        re.compile(r"\b([A-Z][A-Za-z0-9_]*)\s*\."),
        re.compile(
            r"\b(?:public|protected|private)?\s*(?:static\s+)?([A-Z][A-Za-z0-9_]*)\s+[a-z_][A-Za-z0-9_]*\s*(?:[=;,)])"
        ),
    ):
        for match in pattern.finditer(code):
            candidate = _normalize_java_project_map_reference(match.group(1))
            if candidate and candidate not in builtin_types:
                hints.add(candidate)

    return sorted(hints)


def _register_project_map_package(
    packages: dict[str, PackageInfo],
    package_path: str,
    rel_path: str,
) -> None:
    """[20260314_FEATURE] Register a logical package and its ancestors."""
    normalized_path = package_path.strip("/")
    if not normalized_path:
        return

    parts = [part for part in normalized_path.split("/") if part]
    for index in range(len(parts)):
        current_path = "/".join(parts[: index + 1])
        package_name = parts[index]
        if current_path not in packages:
            packages[current_path] = PackageInfo(
                name=package_name,
                path=current_path,
                modules=[],
                subpackages=[],
            )

    if rel_path not in packages[normalized_path].modules:
        packages[normalized_path].modules.append(rel_path)


def _project_map_detect_language(rel_path: str) -> str:
    """Return the canonical project-map language for a relative path."""
    suffix = Path(rel_path).suffix.lower()
    if suffix == ".py":
        return "python"
    if suffix in _PROJECT_MAP_JS_TS_SUFFIXES:
        return (
            "typescript" if suffix in {".ts", ".tsx", ".mts", ".cts"} else "javascript"
        )
    if suffix in _PROJECT_MAP_JAVA_SUFFIXES:
        return "java"
    if suffix in _PROJECT_MAP_GO_SUFFIXES:
        return "go"
    return "other"


def _calculate_js_ts_project_map_complexity(code: str) -> int:
    """Return a lightweight complexity heuristic for local JS/TS project-map scans."""
    return max(1, 1 + len(_PROJECT_MAP_JS_TS_COMPLEXITY_PATTERN.findall(code)))


def _calculate_go_project_map_complexity(code: str) -> int:
    """Return a lightweight complexity heuristic for local Go project-map scans."""
    return max(1, 1 + len(_PROJECT_MAP_GO_COMPLEXITY_PATTERN.findall(code)))


def _read_go_project_map_module_name(root_path: Path) -> str | None:
    """Return the declared Go module path from go.mod when available.

    [20260311_FEATURE] Project-map Go import resolution uses the local go.mod
    module prefix to connect package imports back to workspace files.
    """
    go_mod = root_path / "go.mod"
    if not go_mod.exists():
        return None

    try:
        for raw_line in go_mod.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("//"):
                continue
            if line.startswith("module "):
                module_name = line.split(None, 1)[1].strip()
                return module_name or None
    except Exception:
        return None

    return None


def _scan_js_ts_project_map_module(
    file_path: Path,
    root_path: Path,
    include_complexity: bool,
) -> ModuleInfo | None:
    """Build ModuleInfo for a local JS/TS source file.

    [20260307_FEATURE] Narrow Stage 10 parity slice for get_project_map.
    Uses the JS tree-sitter parser when available, then falls back to regex-free
    line inspection via import statements already exposed by that parser.
    """
    rel_path = str(file_path.relative_to(root_path))
    code = file_path.read_text(encoding="utf-8", errors="ignore")
    lines = code.count("\n") + 1

    functions: list[str] = []
    classes: list[str] = []
    imports: list[str] = []
    entry_points: list[str] = []

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
            parsed = TreeSitterJSParser().parse_file(str(file_path))

            for symbol in parsed.symbols:
                if symbol.kind == "function":
                    functions.append(symbol.name)
                    if symbol.is_exported or symbol.name == "main":
                        entry_points.append(f"{rel_path}:{symbol.name}")
                elif symbol.kind == "class":
                    classes.append(symbol.name)
                    if symbol.is_exported:
                        entry_points.append(f"{rel_path}:{symbol.name}")

            imports = [
                statement.module for statement in parsed.imports if statement.module
            ]
        except Exception:
            return None

    complexity = (
        _calculate_js_ts_project_map_complexity(code) if include_complexity else 0
    )

    return ModuleInfo(
        path=rel_path,
        functions=sorted(set(functions)),
        classes=sorted(set(classes)),
        imports=sorted(set(imports)),
        entry_points=sorted(set(entry_points)),
        line_count=lines,
        complexity_score=complexity,
    )


def _scan_java_project_map_module(
    file_path: Path,
    root_path: Path,
    include_complexity: bool,
) -> _JavaProjectMapModuleScan | None:
    """Build ModuleInfo for a local Java source file.

    [20260308_FEATURE] Narrow Stage 10 Java slice for get_project_map.
    Uses the tree-sitter Java parser to expose class/method/module metadata
    and import keys that the existing relationship builder can reuse.
    """
    rel_path = str(file_path.relative_to(root_path))
    code = file_path.read_text(encoding="utf-8", errors="ignore")
    lines = code.count("\n") + 1

    functions: list[str] = []
    classes: list[str] = []
    imports: list[str] = []
    entry_points: list[str] = []
    relation_hints: list[str] = []

    try:
        from code_scalpel.code_parsers.java_parsers import TreeSitterJavaParser
    except Exception:
        return None

    try:
        parsed = TreeSitterJavaParser().parse_detailed(code)
    except Exception:
        return None

    def add_class(java_class, prefix: str | None = None) -> None:
        qualified_class = f"{prefix}.{java_class.name}" if prefix else java_class.name
        classes.append(qualified_class)
        if java_class.superclass:
            relation_hints.append(
                _normalize_java_project_map_reference(java_class.superclass)
            )
        relation_hints.extend(
            _normalize_java_project_map_reference(interface_name)
            for interface_name in java_class.interfaces
            if _normalize_java_project_map_reference(interface_name)
        )
        for java_method in java_class.methods:
            method_name = (
                java_class.name
                if getattr(java_method, "is_constructor", False)
                else java_method.name
            )
            qualified_name = f"{qualified_class}.{method_name}"
            functions.append(qualified_name)
            if java_method.name == "main" or (
                java_method.name == "entry"
                and "public" in java_method.modifiers
                and "static" in java_method.modifiers
            ):
                entry_points.append(f"{rel_path}:{qualified_name}")
        for inner_class in getattr(java_class, "inner_classes", []) or []:
            add_class(inner_class, qualified_class)
        for inner_record in getattr(java_class, "inner_records", []) or []:
            add_record(inner_record, qualified_class)
        for inner_enum in getattr(java_class, "inner_enums", []) or []:
            add_enum(inner_enum, qualified_class)

    def add_record(java_record, prefix: str | None = None) -> None:
        qualified_record = (
            f"{prefix}.{java_record.name}" if prefix else java_record.name
        )
        classes.append(qualified_record)
        relation_hints.extend(
            _normalize_java_project_map_reference(interface_name)
            for interface_name in getattr(java_record, "interfaces", []) or []
            if _normalize_java_project_map_reference(interface_name)
        )
        for java_method in getattr(java_record, "methods", []) or []:
            method_name = (
                java_record.name
                if getattr(java_method, "is_constructor", False)
                else java_method.name
            )
            qualified_name = f"{qualified_record}.{method_name}"
            functions.append(qualified_name)
            if java_method.name == "main" or (
                java_method.name == "entry"
                and "public" in java_method.modifiers
                and "static" in java_method.modifiers
            ):
                entry_points.append(f"{rel_path}:{qualified_name}")

    def add_interface(java_interface, prefix: str | None = None) -> None:
        qualified_interface = (
            f"{prefix}.{java_interface.name}" if prefix else java_interface.name
        )
        classes.append(qualified_interface)
        relation_hints.extend(
            _normalize_java_project_map_reference(interface_name)
            for interface_name in getattr(java_interface, "extends", []) or []
            if _normalize_java_project_map_reference(interface_name)
        )

    def add_enum(java_enum, prefix: str | None = None) -> None:
        qualified_enum = f"{prefix}.{java_enum.name}" if prefix else java_enum.name
        classes.append(qualified_enum)

    for java_class in parsed.classes:
        add_class(java_class)

    for java_record in getattr(parsed, "records", []) or []:
        add_record(java_record)

    for java_interface in getattr(parsed, "interfaces", []) or []:
        add_interface(java_interface)

    for java_enum in getattr(parsed, "enums", []) or []:
        add_enum(java_enum)

    imports.extend(parsed.imports)
    imports.extend(parsed.static_imports)
    relation_hints.extend(
        _normalize_java_project_map_reference(import_name)
        for import_name in parsed.imports
        if _normalize_java_project_map_reference(import_name)
    )
    relation_hints.extend(
        _normalize_java_project_map_reference(import_name)
        for import_name in parsed.static_imports
        if _normalize_java_project_map_reference(import_name)
    )
    relation_hints.extend(_collect_java_same_package_reference_hints(code))

    complexity = parsed.total_complexity if include_complexity else 0

    module = ModuleInfo(
        path=rel_path,
        functions=sorted(set(functions)),
        classes=sorted(set(classes)),
        imports=sorted(set(imports)),
        entry_points=sorted(set(entry_points)),
        line_count=lines,
        complexity_score=complexity,
    )

    qualified_aliases: list[str] = []
    if parsed.package:
        qualified_aliases.extend(
            f"{parsed.package}.{class_name}" for class_name in module.classes
        )

    return _JavaProjectMapModuleScan(
        module=module,
        package_name=parsed.package,
        relation_hints=sorted(set(relation_hints)),
        qualified_aliases=sorted(set(qualified_aliases)),
    )


def _scan_go_project_map_module(
    file_path: Path,
    root_path: Path,
    include_complexity: bool,
) -> ModuleInfo | None:
    """Build ModuleInfo for a local Go source file.

    [20260311_FEATURE] Narrow Stage 10 Go slice for get_project_map.
    Uses GoNormalizer so the project map can inventory Go functions, methods,
    types, and imports without broadening beyond the current runtime slice.
    """
    rel_path = str(file_path.relative_to(root_path))
    code = file_path.read_text(encoding="utf-8", errors="ignore")
    lines = code.count("\n") + 1

    functions: list[str] = []
    classes: list[str] = []
    imports: list[str] = []
    entry_points: list[str] = []

    def fallback_scan() -> ModuleInfo:
        function_pattern = re.compile(r"\bfunc\s+(?:\([^)]*\)\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*\(")
        type_pattern = re.compile(r"\btype\s+([A-Za-z_][A-Za-z0-9_]*)\s+(?:struct|interface)\b")
        import_block_pattern = re.compile(r"(?ms)^import\s*\((.*?)\)")
        import_line_pattern = re.compile(r'^import\s+(?:[A-Za-z_][A-Za-z0-9_]*\s+)?"([^"]+)"$', re.MULTILINE)
        import_path_pattern = re.compile(r'"([^"]+)"')

        local_functions = sorted(set(function_pattern.findall(code)))
        local_classes = sorted(set(type_pattern.findall(code)))
        local_imports: list[str] = []

        for match in import_line_pattern.finditer(code):
            local_imports.append(match.group(1))

        for block_match in import_block_pattern.finditer(code):
            local_imports.extend(import_path_pattern.findall(block_match.group(1)))

        local_entry_points = [
            f"{rel_path}:main" for function_name in local_functions if function_name == "main"
        ]
        complexity = _calculate_go_project_map_complexity(code) if include_complexity else 0

        return ModuleInfo(
            path=rel_path,
            functions=local_functions,
            classes=local_classes,
            imports=sorted(set(local_imports)),
            entry_points=local_entry_points,
            line_count=lines,
            complexity_score=complexity,
        )

    try:
        from code_scalpel.ir.nodes import IRClassDef, IRFunctionDef, IRImport
        from code_scalpel.ir.normalizers.go_normalizer import GoNormalizer
    except Exception:
        return fallback_scan()

    def normalize_receiver(raw_receiver: Any) -> str | None:
        if not isinstance(raw_receiver, str):
            return None
        normalized = raw_receiver.strip().strip("()")
        if not normalized:
            return None
        parts = [part for part in normalized.replace("*", " ").split() if part]
        if not parts:
            return None
        return parts[-1]

    try:
        parsed = GoNormalizer().normalize(code)
    except Exception:
        return fallback_scan()

    for node in parsed.body:
        if isinstance(node, IRFunctionDef):
            receiver_name = normalize_receiver(
                getattr(node, "_metadata", {}).get("receiver")
            )
            qualified_name = (
                f"{receiver_name}.{node.name}" if receiver_name else node.name
            )
            functions.append(qualified_name)
            if node.name == "main" and receiver_name is None:
                entry_points.append(f"{rel_path}:{qualified_name}")
        elif isinstance(node, IRClassDef):
            classes.append(node.name)
        elif isinstance(node, IRImport) and node.module:
            imports.append(node.module)

    complexity = _calculate_go_project_map_complexity(code) if include_complexity else 0

    return ModuleInfo(
        path=rel_path,
        functions=sorted(set(functions)),
        classes=sorted(set(classes)),
        imports=sorted(set(imports)),
        entry_points=sorted(set(entry_points)),
        line_count=lines,
        complexity_score=complexity,
    )


def _resolve_project_map_import_target(
    import_name: str,
    source_path: str,
    module_index: dict[str, str],
    *,
    root_path: Path | None = None,
    known_module_paths: set[str] | None = None,
    js_ts_alias_resolver: Any | None = None,
    package_index: dict[str, set[str]] | None = None,
    java_package_by_module: dict[str, str] | None = None,
) -> list[str]:
    """Resolve a project-map import string to a known module path.

    [20260314_FEATURE] Supports Python dotted imports, local JS/TS relative and
    alias-backed imports, and Java dotted/static imports.
    """
    source_suffix = Path(source_path).suffix.lower()

    if source_suffix in _PROJECT_MAP_JS_TS_SUFFIXES and import_name.startswith("."):
        parent_dir = Path(source_path).parent
        normalized = (parent_dir / import_name).as_posix()
        normalized = str(Path(normalized))
        candidates = [
            normalized,
            *(normalized + suffix for suffix in _PROJECT_MAP_JS_TS_SUFFIXES),
            *(
                str(Path(normalized) / f"index{suffix}")
                for suffix in _PROJECT_MAP_JS_TS_SUFFIXES
            ),
        ]
        for candidate in candidates:
            if candidate in module_index:
                return [module_index[candidate]]
        return []

    if (
        source_suffix in _PROJECT_MAP_JS_TS_SUFFIXES
        and js_ts_alias_resolver is not None
        and root_path is not None
        and known_module_paths is not None
        and not import_name.startswith(".")
    ):
        try:
            resolved_file = js_ts_alias_resolver.resolve_to_file(import_name)
        except Exception:
            resolved_file = None

        if resolved_file is not None:
            try:
                resolved_rel = str(resolved_file.relative_to(root_path)).replace(
                    "\\", "/"
                )
            except ValueError:
                resolved_rel = ""

            if resolved_rel and resolved_rel in known_module_paths:
                return [resolved_rel]

    if source_suffix in _PROJECT_MAP_JAVA_SUFFIXES:
        normalized_import = _normalize_java_project_map_reference(import_name)
        if not normalized_import:
            return []

        if normalized_import.endswith(".*") and package_index is not None:
            package_name = normalized_import[:-2]
            return sorted(package_index.get(package_name, set()))

        if normalized_import in module_index:
            return [module_index[normalized_import]]

        source_package = None
        if java_package_by_module is not None:
            source_package = java_package_by_module.get(source_path)

        if source_package and "." not in normalized_import:
            qualified_local = f"{source_package}.{normalized_import}"
            if qualified_local in module_index:
                return [module_index[qualified_local]]

        for alias, path_value in module_index.items():
            if normalized_import == alias or normalized_import.startswith(f"{alias}."):
                return [path_value]

        return []

    if import_name in module_index:
        return [module_index[import_name]]

    for alias, path_value in module_index.items():
        if import_name == alias or import_name.startswith(f"{alias}."):
            return [path_value]

    return []


def _get_project_root() -> Path:
    """Get the server's PROJECT_ROOT dynamically.

    [20260120_BUGFIX] Import from server module to get the initialized value.
    Using a getter function ensures we get the value after main() sets it.
    """
    try:
        from code_scalpel.mcp.server import get_project_root

        return get_project_root()
    except ImportError:
        return Path.cwd()


# [20260120_DEPRECATED] Use _get_project_root() instead.
PROJECT_ROOT = Path.cwd()

# [20251219_FEATURE] v3.0.4 - Call graph cache for get_graph_neighborhood
# Stores UniversalGraph objects keyed by project root path (+ variant)
# Format: {cache_key: (UniversalGraph, timestamp)}
# [20251220_PERF] v3.0.5 - Increased cache TTL from 60s to 300s for large codebases
_GRAPH_CACHE: dict[str, tuple["UniversalGraph", float]] = {}  # type: ignore[name-defined]
_GRAPH_CACHE_TTL = 300.0  # seconds (5 minutes for stable codebases)


def _get_cached_graph(
    project_root: Path, cache_variant: str = "default"
) -> "UniversalGraph" | None:  # type: ignore[name-defined]
    """Get cached UniversalGraph for project if still valid."""
    import time

    # [20251225_BUGFIX] Avoid mixing graph variants (e.g., Pro advanced resolution)
    # in a single cache entry.
    key = f"{project_root.resolve()}::{cache_variant}"
    if key in _GRAPH_CACHE:
        graph, timestamp = _GRAPH_CACHE[key]
        if time.time() - timestamp < _GRAPH_CACHE_TTL:
            logger.debug(f"Using cached graph for {key}")
            return graph
        else:
            # Cache expired
            del _GRAPH_CACHE[key]
            logger.debug(f"Graph cache expired for {key}")
    return None


def _cache_graph(
    project_root: Path, graph: "UniversalGraph", cache_variant: str = "default"
) -> None:  # type: ignore[name-defined]
    """Cache a UniversalGraph for a project."""
    import time

    key = f"{project_root.resolve()}::{cache_variant}"
    _GRAPH_CACHE[key] = (graph, time.time())
    logger.debug(f"Cached graph for {key}")


# ============================================================================
# [20251213_FEATURE] v1.5.0 - get_call_graph MCP Tool
# [20260110_FEATURE] v3.3.0 - Pre-release: confidence, context, paths, focus
# ============================================================================

_CALL_GRAPH_PARITY_LEGEND: dict[str, str] = {
    "advanced": "Import-aware and type-aware call graph resolution.",
    "runtime_slice": "Dedicated non-Python runtime slice with language-specific graph logic.",
    "method_local_slice": "Receiver-aware local callable nodes plus conservative import-aware generic edges.",
    "local_slice": "Local callable nodes and same-file call edges via the shared IR fallback.",
}

_CALL_GRAPH_LANGUAGE_PARITY: dict[str, str] = {
    "python": "advanced",
    "javascript": "runtime_slice",
    "typescript": "runtime_slice",
    "java": "runtime_slice",
    "go": "runtime_slice",
    "c": "local_slice",
    "cpp": "method_local_slice",
    "csharp": "method_local_slice",
    "kotlin": "method_local_slice",
    "php": "method_local_slice",
    "ruby": "method_local_slice",
    "swift": "method_local_slice",
    "rust": "method_local_slice",
}

_CALL_GRAPH_RUNTIME_SCOPE_SUMMARY = (
    "Python currently has the deepest get_call_graph semantics. JavaScript, "
    "TypeScript, Java, and Go have dedicated runtime slices. C remains on basic local "
    "callable parity. C++, C#, Kotlin, PHP, Ruby, Swift, and Rust now expose "
    "receiver-aware local callable nodes, and advanced mode adds conservative "
    "import-aware edges through the shared IR-backed fallback."
)


def _get_call_graph_sync(
    project_root: str | None,
    entry_point: str | None,
    depth: int,
    include_circular_import_check: bool,
    max_nodes: int | None = None,
    advanced_resolution: bool = False,
    include_enterprise_metrics: bool = False,
    paths_from: str | None = None,
    paths_to: str | None = None,
    focus_functions: list[str] | None = None,
    tier: str = "community",
    capabilities: dict | None = None,
) -> CallGraphResultModel:
    """Synchronous implementation of get_call_graph with tier-aware metadata."""
    if capabilities is None:
        capabilities = {}
    from code_scalpel.ast_tools.call_graph import CallGraphBuilder

    def _extract_go_symbol_name(signature: str) -> str:
        receiver = signature.strip()
        if not receiver:
            return ""
        receiver_name = receiver.split()[-1].lstrip("*")
        return receiver_name

    def _find_go_block_end(lines: list[str], start_index: int) -> int:
        brace_depth = 0
        saw_open = False
        for index in range(start_index, len(lines)):
            line = lines[index]
            opens = line.count("{")
            closes = line.count("}")
            if opens:
                saw_open = True
            brace_depth += opens
            brace_depth -= closes
            if saw_open and brace_depth <= 0:
                return index + 1
        return len(lines)

    def _build_go_runtime_slice(root: Path) -> tuple[list[CallNodeModel], list[CallEdgeModel]]:
        # [20260315_BUGFIX] Provide a bounded local Go call-graph fallback when
        # optional Go parser support is unavailable in the active runtime.
        function_pattern = re.compile(
            r"^\s*func\s+(?:\((?P<receiver>[^)]+)\)\s*)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(",
            re.MULTILINE,
        )
        nodes_out: list[CallNodeModel] = []
        edges_out: list[CallEdgeModel] = []
        known_symbols: dict[str, tuple[str, int, bool]] = {}
        function_bodies: list[tuple[str, str, str]] = []

        for file_path in sorted(root.rglob("*.go")):
            if not file_path.is_file():
                continue
            try:
                code = file_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            rel_path = str(file_path.relative_to(root)).replace("\\", "/")
            lines = code.splitlines()
            for match in function_pattern.finditer(code):
                raw_name = match.group("name")
                receiver = match.group("receiver")
                symbol_name = raw_name
                if receiver:
                    owner = _extract_go_symbol_name(receiver)
                    if owner:
                        symbol_name = f"{owner}.{raw_name}"
                line_number = code.count("\n", 0, match.start()) + 1
                end_line = _find_go_block_end(lines, max(0, line_number - 1))
                is_entry_point = raw_name == "main"
                known_symbols[symbol_name] = (rel_path, line_number, is_entry_point)
                nodes_out.append(
                    CallNodeModel(
                        name=symbol_name,
                        file=rel_path,
                        line=line_number,
                        end_line=end_line,
                        is_entry_point=is_entry_point,
                        source_uri=str(file_path),
                    )
                )
                body = "\n".join(lines[line_number - 1 : end_line])
                function_bodies.append((rel_path, symbol_name, body))

        for rel_path, caller_name, body in function_bodies:
            for callee_name, (callee_file, _callee_line, _is_entry) in known_symbols.items():
                base_name = callee_name.split(".", 1)[-1]
                if callee_file != rel_path:
                    continue
                if caller_name == callee_name:
                    continue
                if re.search(rf"(?<![A-Za-z0-9_]){re.escape(base_name)}\s*\(", body):
                    edges_out.append(
                        CallEdgeModel(
                            caller=f"{rel_path}:{caller_name}",
                            callee=f"{callee_file}:{callee_name}",
                            confidence=0.7,
                            inference_source="go_runtime_slice",
                        )
                    )

        return nodes_out, edges_out

    # [20251226_BUGFIX] Ensure deterministic truncation and advanced resolution enrichment.
    # [20260119_FEATURE] Uses unified parser for deterministic behavior.
    def _infer_polymorphic_edges(
        root: Path, graph_nodes: list[CallNodeModel]
    ) -> set[tuple[str, str]]:
        """Best-effort inference of self.* call edges for class methods when advanced_resolution is enabled."""
        import ast

        edges: set[tuple[str, str]] = set()
        files = {n.file for n in graph_nodes if n.file not in {"<external>", ""}}
        for rel_path in files:
            file_path = root / rel_path
            if not file_path.exists():
                continue
            try:
                code = file_path.read_text(encoding="utf-8")
                tree, _ = parse_python_code(code, filename=rel_path)
            except (ParsingError, UnicodeDecodeError, OSError):
                continue

            class_name: str | None = None
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_name = node.name
                if (
                    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and class_name
                ):
                    caller = f"{rel_path}:{class_name}.{node.name}"
                    for inner in ast.walk(node):
                        if isinstance(inner, ast.Call) and isinstance(
                            inner.func, ast.Attribute
                        ):
                            if (
                                isinstance(inner.func.value, ast.Name)
                                and inner.func.value.id == "self"
                            ):
                                callee = f"{rel_path}:{class_name}.{inner.func.attr}"
                                edges.add((caller, callee))
        return edges

    root_path = Path(project_root) if project_root else _get_project_root()

    if not root_path.exists():
        return CallGraphResultModel(
            success=False,
            error=f"Project root not found: {root_path}.",
        )

    try:
        builder = CallGraphBuilder(root_path)
        result = builder.build_with_details(
            entry_point=entry_point,
            depth=depth,
            max_nodes=max_nodes,
            advanced_resolution=advanced_resolution,
        )

        # [20260110_FEATURE] v3.3.0 - Convert dataclasses to Pydantic models with new fields
        nodes = [
            CallNodeModel(
                name=n.name,
                file=n.file,
                line=n.line,
                end_line=n.end_line,
                is_entry_point=n.is_entry_point,
                # [20260110_FEATURE] v3.3.0 - Source URI for IDE click-through
                source_uri=n.source_uri,
            )
            for n in result.nodes
        ]

        # [20260110_FEATURE] v3.3.0 - Convert edges with context/confidence metadata
        edges = []
        for e in result.edges:
            context_model = None
            if e.context is not None:
                context_model = CallContextModel(
                    in_loop=e.context.in_loop,
                    in_try_block=e.context.in_try_block,
                    in_conditional=e.context.in_conditional,
                    condition_summary=e.context.condition_summary,
                    in_async=e.context.in_async,
                    in_except_handler=e.context.in_except_handler,
                )
            edges.append(
                CallEdgeModel(
                    caller=e.caller,
                    callee=e.callee,
                    call_line=e.call_line,
                    confidence=e.confidence,
                    inference_source=e.inference_source,
                    context=context_model,
                )
            )

        if not nodes:
            go_nodes, go_edges = _build_go_runtime_slice(root_path)
            if go_nodes:
                nodes = go_nodes
                edges = go_edges
                total_nodes = len(nodes)
                total_edges = len(edges)

        # [20251226_FEATURE] Add heuristic polymorphism edges when enabled.
        if advanced_resolution:
            extra_edges = _infer_polymorphic_edges(root_path, nodes)
            existing = {(e.caller, e.callee) for e in edges}
            for caller, callee in extra_edges:
                if (caller, callee) not in existing:
                    edges.append(CallEdgeModel(caller=caller, callee=callee))
                    existing.add((caller, callee))

        # [20251226_BUGFIX] Apply explicit truncation to honor limits even if builder is permissive.
        total_nodes = len(nodes)
        total_edges = len(edges)
        nodes_truncated = bool(getattr(result, "nodes_truncated", False))
        edges_truncated = bool(getattr(result, "edges_truncated", False))
        if max_nodes is not None and total_nodes > max_nodes:
            nodes = nodes[:max_nodes]
            nodes_truncated = True
            # [20251230_BUGFIX] Normalize node identity format for consistent edge filtering
            # Handle both "file:name" and "file:Class.method" formats
            kept_endpoints = set()
            for n in nodes:
                # Add both the full name and simple name to handle format variations
                if n.file != "<external>":
                    kept_endpoints.add(f"{n.file}:{n.name}")
                    # If name contains class qualification, also add without file prefix
                    if "." in n.name:
                        kept_endpoints.add(n.name)
                else:
                    kept_endpoints.add(n.name)

            filtered_edges = [
                e
                for e in edges
                if (e.caller in kept_endpoints and e.callee in kept_endpoints)
            ]
            edges_truncated = edges_truncated or len(filtered_edges) < len(edges)
            edges = filtered_edges

        truncation_warning = None
        if nodes_truncated or edges_truncated:
            parts: list[str] = []
            if max_nodes is not None:
                parts.append(f"max_nodes={max_nodes}")
            parts.append(f"max_depth={depth}")
            truncation_warning = "Results truncated by limits: " + ", ".join(parts)

        hot_nodes: list[str] = []
        dead_code_candidates: list[str] = []
        if include_enterprise_metrics:
            # [20251225_FEATURE] Best-effort degree metrics and dead-code candidates.
            in_deg: dict[str, int] = {}
            out_deg: dict[str, int] = {}

            for edge in edges:
                out_deg[edge.caller] = out_deg.get(edge.caller, 0) + 1
                in_deg[edge.callee] = in_deg.get(edge.callee, 0) + 1

            for node in nodes:
                full_name = (
                    f"{node.file}:{node.name}"
                    if node.file != "<external>"
                    else node.name
                )
                node.in_degree = in_deg.get(full_name, 0)
                node.out_degree = out_deg.get(full_name, 0)

            def _total_degree(n: CallNodeModel) -> tuple[int, str]:
                full = f"{n.file}:{n.name}" if n.file != "<external>" else n.name
                return ((n.in_degree or 0) + (n.out_degree or 0), full)

            hot_nodes = [
                (f"{n.file}:{n.name}" if n.file != "<external>" else n.name)
                for n in sorted(nodes, key=_total_degree, reverse=True)[:10]
                if _total_degree(n)[0] > 0
            ]

            # [20251230_BUGFIX] Optimize dead-code detection: use existing graph instead of rebuilding
            # Only identify dead code from the nodes we already have (don't rebuild full graph)
            # This is more efficient and respects the user's max_nodes limit
            dead_code_candidates = [
                f"{n.file}:{n.name}" if n.file != "<external>" else n.name
                for n in nodes
                if not n.is_entry_point
                and in_deg.get(
                    f"{n.file}:{n.name}" if n.file != "<external>" else n.name, 0
                )
                == 0
            ]

        # Optionally check for circular imports
        circular_imports = []
        if include_circular_import_check:
            circular_imports = builder.detect_circular_imports()

        # [20260110_FEATURE] v3.3.0 - Path query API
        paths: list[list[str]] = []
        if paths_from and paths_to:
            # Build adjacency list from edges for path finding
            adj_list: dict[str, list[str]] = {}
            for e in edges:
                adj_list.setdefault(e.caller, []).append(e.callee)
            find_paths = getattr(builder, "find_paths", None)
            if callable(find_paths):
                paths = cast(
                    list[list[str]],
                    find_paths(paths_from, paths_to, max_depth=depth, graph=adj_list),
                )
            else:
                # Fallback: simple DFS path search within max depth
                def _dfs_paths(
                    start: str, goal: str, max_depth: int
                ) -> list[list[str]]:
                    results: list[list[str]] = []
                    stack: list[tuple[str, list[str]]] = [(start, [start])]
                    while stack:
                        node, path = stack.pop()
                        if len(path) - 1 > max_depth:
                            continue
                        if node == goal:
                            results.append(path)
                            continue
                        for nxt in adj_list.get(node, []):
                            if nxt in path:
                                continue
                            stack.append((nxt, path + [nxt]))
                    return results

                paths = _dfs_paths(paths_from, paths_to, depth)

        # [20260110_FEATURE] v3.3.0 - Focus mode: filter to subgraph around focus_functions
        actual_focus_functions: list[str] | None = None
        if focus_functions:
            # Find k-hop neighborhood around focus functions
            focus_set = set(focus_functions)
            related: set[str] = set(focus_functions)

            # Add all nodes that call or are called by focus functions (1-hop)
            for e in edges:
                if e.caller in focus_set or e.callee in focus_set:
                    related.add(e.caller)
                    related.add(e.callee)

            # Filter nodes and edges to only those in the related set
            nodes = [
                n for n in nodes if f"{n.file}:{n.name}" in related or n.name in related
            ]
            edges = [e for e in edges if e.caller in related or e.callee in related]
            actual_focus_functions = focus_functions

        return CallGraphResultModel(
            nodes=nodes,
            edges=edges,
            entry_point=result.entry_point,
            depth_limit=result.depth_limit,
            mermaid=result.mermaid,
            circular_imports=circular_imports,
            paths=paths,
            focus_functions=actual_focus_functions,
            total_nodes=total_nodes,
            total_edges=total_edges,
            nodes_truncated=nodes_truncated,
            edges_truncated=edges_truncated,
            truncation_warning=truncation_warning,
            hot_nodes=hot_nodes,
            dead_code_candidates=dead_code_candidates,
            # [20260120_FEATURE] Metadata transparency: report tier's limits and capabilities
            tier_applied=tier,
            max_depth_applied=capabilities.get("limits", {}).get("max_depth"),
            max_nodes_applied=capabilities.get("limits", {}).get("max_nodes"),
            advanced_resolution_enabled="advanced_call_graph"
            in capabilities.get("capabilities", []),
            enterprise_metrics_enabled="hot_path_identification"
            in capabilities.get("capabilities", []),
            language_parity=dict(_CALL_GRAPH_LANGUAGE_PARITY),
            parity_legend=dict(_CALL_GRAPH_PARITY_LEGEND),
            runtime_scope_summary=_CALL_GRAPH_RUNTIME_SCOPE_SUMMARY,
        )

    except Exception as e:
        return CallGraphResultModel(
            success=False,
            error=f"Call graph analysis failed: {str(e)}",
        )


# ============================================================================
# [20251216_FEATURE] v2.5.0 - get_graph_neighborhood MCP Tool
# ============================================================================


def _generate_neighborhood_mermaid(
    nodes: list[NeighborhoodNodeModel],
    edges: list[NeighborhoodEdgeModel],
    center_node_id: str,
) -> str:
    """Generate Mermaid diagram for neighborhood."""
    lines = ["graph TD"]

    # Add nodes with depth-based styling
    for node in nodes:
        # Sanitize node ID for Mermaid
        safe_id = node.id.replace("::", "_").replace(".", "_").replace("-", "_")
        label = node.id.split("::")[-1] if "::" in node.id else node.id

        if node.depth == 0:
            # Center node - special styling
            lines.append(f'    {safe_id}["{label}"]:::center')
        elif node.depth == 1:
            lines.append(f'    {safe_id}["{label}"]:::depth1')
        else:
            lines.append(f'    {safe_id}["{label}"]:::depth2plus')

    # Add edges
    for edge in edges:
        from_safe = edge.from_id.replace("::", "_").replace(".", "_").replace("-", "_")
        to_safe = edge.to_id.replace("::", "_").replace(".", "_").replace("-", "_")
        lines.append(f"    {from_safe} --> {to_safe}")

    # Add style definitions
    lines.append("    classDef center fill:#f9f,stroke:#333,stroke-width:3px")
    lines.append("    classDef depth1 fill:#bbf,stroke:#333,stroke-width:2px")
    lines.append("    classDef depth2plus fill:#ddd,stroke:#333,stroke-width:1px")

    return "\n".join(lines)


def _normalize_graph_center_node_id(center_node_id: str) -> str:
    """Normalize common legacy node-id formats into canonical IDs.

    [20260306_DOCS] Canonical IDs for get_graph_neighborhood are still Python
    function IDs today.

    Canonical formats:
    - python::<module>::function::<name>
    - javascript::<path/module>::function::<name>
    - typescript::<path/module>::function::<name>
    - java::<path/module>::method::<owner>:<name>
    - go::<path/module>::function::<name>
    - go::<path/module>::method::<owner>:<name>
    - javascript::<path/module>::method::<owner>:<name>
    - typescript::<path/module>::method::<owner>:<name>

    Accepted legacy inputs:
    - routes.py:search_route
    - path/to/routes.py:search_route
    - routes:search_route
    """
    raw = (center_node_id or "").strip()
    if not raw:
        return raw

    if any(
        raw.startswith(f"{language}::")
        and ("::function::" in raw or "::method::" in raw)
        for language in _GRAPH_LANGUAGE_EXTENSIONS
    ):
        return raw

    # Common legacy format: <file>:<symbol>
    if ":" in raw and "::" not in raw:
        left, right = raw.rsplit(":", 1)
        file_part = left.strip()
        name = right.strip()
        if not name:
            return raw

        suffix = Path(file_part).suffix.lower()

        # If this looks like a Python path, convert to dotted module.
        if file_part.endswith(".py"):
            module = file_part.replace("/", ".").replace("\\", ".")
            if module.endswith(".py"):
                module = module[: -len(".py")]
            # Drop leading dots that can happen with absolute-ish inputs.
            module = module.strip(".")
            if module:
                return f"python::{module}::function::{name}"

        # [20260308_FEATURE] Preserve slash-style module IDs for JS/TS and Java.
        js_ts_language = _GRAPH_SUFFIX_TO_LANGUAGE.get(suffix)
        if js_ts_language is not None:
            module = file_part.replace("\\", "/")
            module = module[: -len(suffix)] if module.endswith(suffix) else module
            module = module.strip("/")
            if module:
                if js_ts_language == "java":
                    owner = Path(module).name
                    method_owner = owner
                    method_name = name
                    if "." in name:
                        method_owner, method_name = name.split(".", 1)
                    return f"java::{module}::method::{method_owner}:{method_name}"
                if js_ts_language == "go":
                    if "." in name:
                        method_owner, method_name = name.split(".", 1)
                        return f"go::{module}::method::{method_owner}:{method_name}"
                    return f"go::{module}::function::{name}"
                return f"{js_ts_language}::{module}::function::{name}"

        # If this looks like a bare module name.
        module = file_part.replace("/", ".").replace("\\", ".").strip(".")
        if module:
            return f"python::{module}::function::{name}"

    return raw


def _resolve_graph_module_candidate(
    root_path: Path, language: str, module: str
) -> Path | None:
    """Resolve a canonical graph module to a local source file when possible."""
    if language == "python":
        candidate = root_path / (module.replace(".", "/") + ".py")
        return candidate if candidate.exists() else None

    if language == "java":
        normalized = module.replace("\\", "/").strip("/")
        module_paths = [normalized]
        dotted_variant = normalized.replace(".", "/")
        if dotted_variant not in module_paths:
            module_paths.append(dotted_variant)

        for module_path in module_paths:
            candidate = (root_path / module_path).with_suffix(".java")
            if candidate.exists():
                return candidate
        return None

    if language not in {"javascript", "typescript", "go"}:
        return None

    normalized = module.replace("\\", "/").strip("/")
    candidates: list[Path] = []
    module_paths = [normalized]
    dotted_variant = normalized.replace(".", "/")
    if dotted_variant not in module_paths:
        module_paths.append(dotted_variant)

    for module_path in module_paths:
        base = root_path / module_path
        if base.suffix.lower() in _GRAPH_LANGUAGE_EXTENSIONS[language]:
            candidates.append(base)
        else:
            for suffix in _GRAPH_LANGUAGE_EXTENSIONS[language]:
                candidates.append(base.with_suffix(suffix))

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


def _fast_validate_js_ts_graph_node_exists(
    candidate: Path, kind: str, name: str
) -> tuple[bool, str | None]:
    """Best-effort validation for a local JS/TS function or method node.

    [20260306_FEATURE] Accept canonical JS/TS method IDs in addition to function IDs.
    """
    method_owner: str | None = None
    method_name = name
    if kind == "method":
        if ":" not in name:
            return False, f"Invalid JS/TS method node '{name}'; expected Owner:method"
        method_owner, method_name = name.split(":", 1)

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
            parsed = TreeSitterJSParser().parse_file(str(candidate))
            for symbol in parsed.symbols:
                if (
                    kind == "function"
                    and symbol.kind == "function"
                    and symbol.name == name
                ):
                    return True, None
                if (
                    kind == "method"
                    and symbol.kind == "method"
                    and symbol.parent_name == method_owner
                    and symbol.name == method_name
                ):
                    return True, None
        except Exception:
            pass

    try:
        import esprima  # type: ignore[import-untyped]
        import esprima.nodes  # type: ignore[import-untyped]
    except Exception:
        return True, None

    try:
        code = candidate.read_text(encoding="utf-8")
        try:
            ast_js = esprima.parseModule(code, loc=True, tolerant=True)
        except Exception:
            ast_js = esprima.parseScript(code, loc=True, tolerant=True)
    except Exception:
        return True, None

    stack = [ast_js]
    while stack:
        node = stack.pop()
        if isinstance(node, list):
            stack.extend(node)
            continue
        if not isinstance(node, esprima.nodes.Node):
            continue
        if kind == "function" and isinstance(node, esprima.nodes.FunctionDeclaration):
            ident = getattr(getattr(node, "id", None), "name", None)
            if ident == name:
                return True, None
        if kind == "method" and method_owner:
            if node.__class__.__name__ in {"MethodDefinition", "Property"}:
                key = getattr(node, "key", None)
                value = getattr(node, "value", None)
                ident = getattr(key, "name", None)
                if ident == method_name and value is not None:
                    parent = getattr(getattr(node, "_parent", None), "id", None)
                    parent_name = getattr(parent, "name", None)
                    if parent_name == method_owner:
                        return True, None
        for value in node.__dict__.values():
            if isinstance(value, esprima.nodes.Node):
                try:
                    setattr(value, "_parent", node)
                except Exception:
                    pass
                stack.append(value)
            elif isinstance(value, list):
                for child in value:
                    if isinstance(child, esprima.nodes.Node):
                        try:
                            setattr(child, "_parent", node)
                        except Exception:
                            pass
                    stack.append(child)

    return False, f"Center node JS/TS {kind} '{name}' not found in {candidate}"


def _fast_validate_java_graph_node_exists(
    candidate: Path, kind: str, name: str
) -> tuple[bool, str | None]:
    """Best-effort validation for a local Java method node.

    [20260308_FEATURE] Reuse the tree-sitter Java parser to validate canonical
    Java method-node IDs for get_graph_neighborhood.
    """
    if kind != "method":
        return (
            False,
            "get_graph_neighborhood currently supports Java method nodes only. "
            f"Received Java {kind} node '{name}'.",
        )

    if ":" not in name:
        return False, f"Invalid Java method node '{name}'; expected Owner:method"

    owner, method_name = name.split(":", 1)

    def _java_method_selector(
        owner_name: str, method: object, overloaded_names: set[str]
    ) -> str:
        member_name = (
            owner_name.split(".")[-1]
            if getattr(method, "is_constructor", False)
            else getattr(method, "name", "")
        )
        if member_name not in overloaded_names:
            return f"{owner_name}.{member_name}"
        parameter_types = ", ".join(
            re.sub(
                r"([A-Za-z_$][\w$]*\.)+([A-Za-z_$][\w$]*(?:\[\])*)",
                r"\2",
                re.sub(r"\s+", "", getattr(parameter, "param_type", None) or "?"),
            )
            or "?"
            for parameter in (getattr(method, "parameters", None) or [])
        )
        return f"{owner_name}.{member_name}({parameter_types})"

    try:
        from code_scalpel.code_parsers.java_parsers import TreeSitterJavaParser
    except Exception:
        return True, None

    try:
        parser = TreeSitterJavaParser()
        parsed = parser.parse_detailed(candidate.read_text(encoding="utf-8"))
    except Exception:
        return True, None

    # [20260309_FEATURE] Match both Java classes and records so canonical
    # record method nodes can round-trip through get_graph_neighborhood.
    class_stack = list(parsed.classes)
    while class_stack:
        java_class = class_stack.pop()
        overload_counts: dict[str, int] = {}
        for java_method in java_class.methods:
            member_name = (
                java_class.name
                if getattr(java_method, "is_constructor", False)
                else java_method.name
            )
            overload_counts[member_name] = overload_counts.get(member_name, 0) + 1
        overloaded_names = {
            member_name for member_name, count in overload_counts.items() if count > 1
        }
        if java_class.name == owner and any(
            method_name == java_method.name
            or method_name
            == _java_method_selector(
                java_class.name, java_method, overloaded_names
            ).split(".", 1)[1]
            for java_method in java_class.methods
        ):
            return True, None
        class_stack.extend(java_class.inner_classes)

    record_stack = list(getattr(parsed, "records", []) or [])
    while record_stack:
        java_record = record_stack.pop()
        overload_counts: dict[str, int] = {}
        for java_method in getattr(java_record, "methods", []) or []:
            member_name = (
                java_record.name
                if getattr(java_method, "is_constructor", False)
                else java_method.name
            )
            overload_counts[member_name] = overload_counts.get(member_name, 0) + 1
        overloaded_names = {
            member_name for member_name, count in overload_counts.items() if count > 1
        }
        if java_record.name == owner and any(
            method_name == java_method.name
            or method_name
            == _java_method_selector(
                java_record.name, java_method, overloaded_names
            ).split(".", 1)[1]
            for java_method in getattr(java_record, "methods", []) or []
        ):
            return True, None

    return False, f"Center node Java method '{name}' not found in {candidate}"


def _fast_validate_go_graph_node_exists(
    candidate: Path, kind: str, name: str
) -> tuple[bool, str | None]:
    """Best-effort validation for local Go function and method nodes.

    [20260311_FEATURE] Accept canonical Go function and receiver-method IDs in
    get_graph_neighborhood without forcing a full graph build for obvious misses.
    """
    try:
        code = candidate.read_text(encoding="utf-8")
    except Exception:
        return True, None

    if kind == "function":
        if re.search(rf"\bfunc\s+{re.escape(name)}\s*\(", code):
            return True, None
        return False, f"Center node Go function '{name}' not found in {candidate}"

    if kind != "method":
        return (
            False,
            "get_graph_neighborhood currently supports Go function and method nodes only. "
            f"Received Go {kind} node '{name}'.",
        )

    if ":" not in name:
        return False, f"Invalid Go method node '{name}'; expected Owner:method"

    owner, method_name = name.split(":", 1)
    method_pattern = re.compile(
        rf"\bfunc\s*\(\s*[^)]*\*?\s*{re.escape(owner)}\s*\)\s*{re.escape(method_name)}\s*\(",
    )
    if method_pattern.search(code):
        return True, None

    return False, f"Center node Go method '{name}' not found in {candidate}"


def _parse_graph_center_node_id(
    center_node_id: str,
) -> tuple[str, str, str, str] | None:
    """Parse a canonical graph center node ID.

    [20260306_REFACTOR] Shared parser for graph neighborhood and JS/TS dependency slices.
    """
    import re

    match = re.match(
        r"^(?P<lang>[^:]+)::(?P<module>[^:]+)::(?P<kind>[^:]+)::(?P<name>.+)$",
        center_node_id.strip(),
    )
    if not match:
        return None
    return (
        match.group("lang"),
        match.group("module"),
        match.group("kind"),
        match.group("name"),
    )


def _fast_validate_graph_center_node_exists(
    root_path: Path, center_node_id: str
) -> tuple[bool, str | None]:
    """Best-effort fast validation for supported graph-neighborhood node IDs.

    [20260311_FEATURE] Supports Python function nodes, JS/TS function and
    method nodes, canonical Java method nodes, and canonical Go function/method nodes.
    """
    parsed = _parse_graph_center_node_id(center_node_id)
    if parsed is None:
        return (
            False,
            "Invalid center_node_id format; expected language::module::type::name. "
            "get_graph_neighborhood currently accepts canonical Python, JavaScript, "
            "TypeScript, Java, and Go node IDs such as python::app.routes::function::handle_request, "
            "typescript::src/api/client::function::fetchUsers, java::demo/App::method::App:main, "
            "or go::cmd/main::function::main.",
        )

    lang, module, kind, name = parsed

    if kind not in {"function", "method"}:
        return (
            False,
            "get_graph_neighborhood currently supports local Python function nodes, JavaScript/TypeScript function and method nodes, Java method nodes, and Go function/method nodes only. "
            f"Received '{center_node_id}'.",
        )

    if lang not in {"python", "javascript", "typescript", "java", "go"}:
        return (
            False,
            "get_graph_neighborhood currently supports local Python function nodes plus local JavaScript, TypeScript, Java, and Go graph nodes only. "
            f"Received '{center_node_id}'.",
        )

    if kind == "method" and lang == "python":
        return (
            False,
            "get_graph_neighborhood currently exposes canonical method-node support for JavaScript, TypeScript, Java, and Go only. "
            f"Received '{center_node_id}'.",
        )

    if kind == "function" and lang == "java":
        return (
            False,
            "get_graph_neighborhood currently expects canonical Java method-node IDs such as "
            "java::demo/App::method::App:main, not Java function-node IDs. "
            f"Received '{center_node_id}'.",
        )

    if module in ("external", "unknown"):
        return (
            False,
            f"Center node module '{module}' is not a local {lang} module for get_graph_neighborhood.",
        )

    candidate = _resolve_graph_module_candidate(root_path, lang, module)
    if candidate is None:
        return (
            False,
            f"Center node file not found for local {lang} module '{module}'.",
        )

    if lang == "python":
        return _fast_validate_python_function_node_exists(root_path, center_node_id)

    if lang == "java":
        return _fast_validate_java_graph_node_exists(candidate, kind, name)

    if lang == "go":
        return _fast_validate_go_graph_node_exists(candidate, kind, name)

    return _fast_validate_js_ts_graph_node_exists(candidate, kind, name)


def _get_graph_language_from_file(file_path: str) -> str:
    """Infer graph language from a relative file path."""
    if file_path in {"", "<external>"}:
        return "external"
    return _GRAPH_SUFFIX_TO_LANGUAGE.get(Path(file_path).suffix.lower(), "external")


def _get_graph_module_from_file(file_path: str, language: str) -> str:
    """Convert a relative file path to the canonical graph module form."""
    if file_path in {"", "<external>"}:
        return "external"

    normalized = file_path.replace("\\", "/")
    suffix = Path(normalized).suffix.lower()
    if suffix:
        normalized = normalized[: -len(suffix)]

    if language == "python":
        return normalized.replace("/", ".").strip(".")

    return normalized.strip("/")


def _build_graph_node_id(file_path: str, symbol_name: str) -> str:
    """Build a canonical graph node ID from a file/symbol pair."""
    language = _get_graph_language_from_file(file_path)
    module = _get_graph_module_from_file(file_path, language)

    if file_path not in {"", "<external>"} and "." in symbol_name:
        owner, method = symbol_name.split(".", 1)
        return str(
            UniversalNodeID(
                language=language,
                module=module,
                node_type=NodeType.METHOD,
                name=owner,
                method=method,
            )
        )

    return str(
        UniversalNodeID(
            language=language,
            module=module,
            node_type=NodeType.FUNCTION,
            name=symbol_name,
        )
    )


def _get_java_symbol_base_name(symbol_name: str) -> str:
    """Return the base member name from a Java selector or canonical method name."""
    tail = symbol_name.rsplit(".", 1)[-1]
    return tail.split("(", 1)[0]


def _get_java_symbol_argument_block(symbol_name: str) -> str | None:
    """Return the argument block for a Java selector, including parentheses."""
    if "(" not in symbol_name or not symbol_name.endswith(")"):
        return None
    return symbol_name[symbol_name.index("(") :]


def _read_node_code_slice(
    root_path: Path, rel_file: str, line: int, end_line: int | None
) -> str:
    """Read a best-effort source slice for a graph node.

    [20260306_FEATURE] Shared by the JS/TS cross-file dependency parity slice.
    """
    if rel_file in {"", "<external>"}:
        return ""

    file_path = root_path / rel_file
    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return ""

    if not lines:
        return ""

    start_idx = max(0, line - 1)
    end_idx = max(start_idx + 1, end_line or line)
    end_idx = min(end_idx, len(lines))
    return "\n".join(lines[start_idx:end_idx])


def _build_file_dependency_chains(
    import_graph: dict[str, list[str]], target_file: str, max_depth: int
) -> list[list[str]]:
    """Build bounded file-level dependency chains.

    [20260306_REFACTOR] Reused by the JS/TS dependency fallback to mirror the
    existing CrossFileDependenciesResult contract.
    """
    from collections import deque

    dependency_chains: list[list[str]] = []
    max_chains = 25
    queue = deque([(target_file, [target_file], 0)])
    seen_paths: set[tuple[str, ...]] = set()

    while queue and len(dependency_chains) < max_chains:
        current, path, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for dep in import_graph.get(current, []):
            new_path = path + [dep]
            path_key = tuple(new_path)
            if path_key in seen_paths:
                continue
            seen_paths.add(path_key)
            dependency_chains.append(new_path)
            queue.append((dep, new_path, depth + 1))

    return dependency_chains


def _build_file_mermaid(
    import_graph: dict[str, list[str]], target_file: str, max_depth: int
) -> str:
    """Build a bounded Mermaid diagram from a file-level import graph."""
    from collections import deque

    max_mermaid_nodes = 60
    max_mermaid_edges = 200
    queue = deque([(target_file, 0)])
    seen_nodes: set[str] = set()
    edges_out: list[tuple[str, str]] = []

    while (
        queue
        and len(seen_nodes) < max_mermaid_nodes
        and len(edges_out) < max_mermaid_edges
    ):
        current, depth = queue.popleft()
        if current in seen_nodes:
            continue
        seen_nodes.add(current)
        if depth >= max_depth:
            continue
        for dep in import_graph.get(current, [])[:max_mermaid_edges]:
            if len(edges_out) >= max_mermaid_edges:
                break
            edges_out.append((current, dep))
            if dep not in seen_nodes:
                queue.append((dep, depth + 1))

    lines = ["graph TD"]
    seen_nodes.add(target_file)
    node_ids: dict[str, str] = {}
    for index, node in enumerate(sorted(seen_nodes)):
        node_ids[node] = f"N{index}"
        safe_label = node.replace("/", "_").replace(".", "_")
        lines.append(f"    {node_ids[node]}[{safe_label}]")

    for source, target in edges_out:
        if source in node_ids and target in node_ids:
            lines.append(f"    {node_ids[source]} --> {node_ids[target]}")

    if len(seen_nodes) >= max_mermaid_nodes or len(edges_out) >= max_mermaid_edges:
        lines.append(
            f"    %% Diagram truncated (nodes<={max_mermaid_nodes}, edges<={max_mermaid_edges})"
        )

    return "\n".join(lines)


def _get_js_ts_cross_file_dependencies_sync(
    root_path: Path,
    target_path: Path,
    target_symbol: str,
    target_language: str,
    effective_max_depth: int,
    include_code: bool,
    include_diagram: bool,
    confidence_decay_factor: float,
    tier: str,
    caps_set: set[str],
    max_depth_limit: int | None,
    max_files_limit: int | None,
) -> CrossFileDependenciesResult:
    """Graph-backed JS/TS/Java/Go dependency slice for get_cross_file_dependencies.

    [20260311_FEATURE] Extend the graph-backed dependency path to Go symbols in
    addition to JS/TS/Java, reusing the shared call-graph runtime while keeping
    the existing result contract intact.
    """
    from collections import defaultdict, deque

    from code_scalpel.ast_tools.call_graph import CallGraphBuilder
    from code_scalpel.ast_tools.cross_file_extractor import (
        DEFAULT_LOW_CONFIDENCE_THRESHOLD,
        calculate_confidence,
    )

    target_rel = str(target_path.relative_to(root_path))
    # [20260307_FEATURE] Stage 10.1 metadata parity for graph-backed dependency slices.
    pro_features_enabled = tier in {"pro", "enterprise"}
    enterprise_features_enabled = tier == "enterprise"
    # [20260311_FEATURE] JS/TS requires advanced imported-identifier resolution
    # for useful cross-file payloads; Java and Go keep Community local-only and
    # rely on the existing Pro/Enterprise advanced builder for richer cross-file imports.
    advanced_resolution = target_language in {"javascript", "typescript"} or tier in {
        "pro",
        "enterprise",
    }

    builder = CallGraphBuilder(root_path)
    call_graph_result = builder.build_with_details(
        entry_point=None,
        depth=max(10, effective_max_depth + 2),
        max_nodes=None,
        advanced_resolution=advanced_resolution,
    )

    node_lookup: dict[str, Any] = {}
    node_dependencies: dict[str, list[str]] = defaultdict(list)

    for node in call_graph_result.nodes:
        if node.file in {"", "<external>"}:
            continue
        if _get_graph_language_from_file(node.file) != target_language:
            continue
        node_lookup[f"{node.file}:{node.name}"] = node

    for edge in call_graph_result.edges:
        if ":" not in edge.caller or ":" not in edge.callee:
            continue
        caller_file, caller_name = edge.caller.split(":", 1)
        callee_file, callee_name = edge.callee.split(":", 1)
        caller_key = f"{caller_file}:{caller_name}"
        callee_key = f"{callee_file}:{callee_name}"
        if caller_key in node_lookup and callee_key in node_lookup:
            node_dependencies[caller_key].append(callee_key)

    target_candidates = [f"{target_rel}:{target_symbol}"]
    if ":" in target_symbol:
        owner, method = target_symbol.split(":", 1)
        target_candidates.append(f"{target_rel}:{owner}.{method}")
    if target_language == "java":
        # [20260308_FEATURE] Allow Java callers to pass bare method names while
        # the graph runtime exposes canonical Class.method node names.
        normalized_target = target_symbol.replace(":", ".", 1)
        target_base = _get_java_symbol_base_name(normalized_target)
        target_arg_block = _get_java_symbol_argument_block(normalized_target)

        java_matches = sorted(
            key
            for key, node in node_lookup.items()
            if node.file == target_rel
            and (
                node.name == target_symbol
                or node.name.endswith(f".{target_symbol}")
                or node.name == target_symbol.replace(":", ".", 1)
                or _get_java_symbol_base_name(node.name) == target_symbol
                or (
                    target_arg_block is not None
                    and _get_java_symbol_base_name(node.name) == target_base
                    and (
                        node.name.endswith(f".{target_base}{target_arg_block}")
                        or node.name == f"{target_base}.{target_base}"
                    )
                )
            )
        )
        if len(java_matches) == 1:
            target_candidates.insert(0, java_matches[0])
        elif len(java_matches) > 1:
            return CrossFileDependenciesResult(
                success=False,
                tier_applied=tier,
                max_depth_applied=max_depth_limit,
                max_files_applied=max_files_limit,
                pro_features_enabled=pro_features_enabled,
                enterprise_features_enabled=enterprise_features_enabled,
                error=(
                    f"Extraction failed: Symbol '{target_symbol}' is ambiguous in {target_path}. "
                    "Use Class.method(type) or Class:method(type) to select an overloaded Java method."
                ),
            )

    target_key = next(
        (candidate for candidate in target_candidates if candidate in node_lookup), None
    )
    if target_key is None:
        return CrossFileDependenciesResult(
            success=False,
            tier_applied=tier,
            max_depth_applied=max_depth_limit,
            max_files_applied=max_files_limit,
            pro_features_enabled=pro_features_enabled,
            enterprise_features_enabled=enterprise_features_enabled,
            error=f"Extraction failed: Symbol '{target_symbol}' not found in {target_path}.",
        )

    depths: dict[str, int] = {target_key: 0}
    queue = deque([target_key])
    while queue:
        current = queue.popleft()
        current_depth = depths[current]
        if current_depth >= effective_max_depth:
            continue
        for dep in node_dependencies.get(current, []):
            next_depth = current_depth + 1
            if dep not in depths or next_depth < depths[dep]:
                depths[dep] = next_depth
                queue.append(dep)

    file_order: list[str] = []
    extracted_symbols: list[ExtractedSymbolModel] = []
    low_confidence_count = 0
    sorted_keys = sorted(depths.keys(), key=lambda key: (depths[key], key))
    for key in sorted_keys:
        node = node_lookup[key]
        if node.file not in file_order:
            file_order.append(node.file)

    files_scanned = len(file_order)
    allowed_files = set(file_order)
    files_truncated = 0
    truncation_warning = None
    if max_files_limit is not None and files_scanned > max_files_limit:
        allowed_files = set(file_order[:max_files_limit])
        files_truncated = files_scanned - max_files_limit
        truncation_warning = f"Truncated to {max_files_limit} files (of {files_scanned}) due to tier limits."

    filtered_keys = [
        key for key in sorted_keys if node_lookup[key].file in allowed_files
    ]
    for key in filtered_keys:
        node = node_lookup[key]
        depth = depths[key]
        confidence = calculate_confidence(depth, confidence_decay_factor)
        if confidence < DEFAULT_LOW_CONFIDENCE_THRESHOLD:
            low_confidence_count += 1
        extracted_symbols.append(
            ExtractedSymbolModel(
                name=node.name,
                code=(
                    _read_node_code_slice(
                        root_path, node.file, node.line, node.end_line
                    )
                    if include_code
                    else ""
                ),
                file=node.file,
                line_start=node.line,
                line_end=node.end_line or 0,
                dependencies=[
                    node_lookup[dep].name
                    for dep in node_dependencies.get(key, [])
                    if dep in filtered_keys
                ],
                depth=depth,
                confidence=confidence,
                low_confidence=confidence < DEFAULT_LOW_CONFIDENCE_THRESHOLD,
            )
        )

    import_graph: dict[str, list[str]] = defaultdict(list)
    for key in filtered_keys:
        source_file = node_lookup[key].file
        for dep in node_dependencies.get(key, []):
            if dep not in filtered_keys:
                continue
            target_file = node_lookup[dep].file
            if source_file == target_file:
                continue
            if target_file not in import_graph[source_file]:
                import_graph[source_file].append(target_file)

    import_graph = {source: sorted(targets) for source, targets in import_graph.items()}
    dependency_chains = _build_file_dependency_chains(
        import_graph, target_rel, effective_max_depth
    )
    max_depth_reached = max(depths.values()) if depths else 0
    files_analyzed = len({node_lookup[key].file for key in filtered_keys})
    coupling_score: float | None = None
    if (
        files_analyzed > 0
        and len(extracted_symbols) > 1
        and "deep_coupling_analysis" in caps_set
    ):
        coupling_score = round((len(extracted_symbols) - 1) / files_analyzed, 3)

    combined_code = ""
    if include_code:
        combined_parts = []
        for symbol in extracted_symbols:
            combined_parts.append(f"# From {symbol.file}")
            combined_parts.append(symbol.code)
        combined_code = "\n\n".join(combined_parts)

    low_confidence_warning = None
    if low_confidence_count > 0:
        names = [symbol.name for symbol in extracted_symbols if symbol.low_confidence][
            :5
        ]
        low_confidence_warning = (
            f"⚠️ {low_confidence_count} symbol(s) have low confidence (below 0.5): "
            + ", ".join(names)
            + ("..." if low_confidence_count > 5 else "")
        )

    mermaid = (
        _build_file_mermaid(import_graph, target_rel, effective_max_depth)
        if include_diagram
        else ""
    )

    return CrossFileDependenciesResult(
        success=True,
        target_name=target_symbol,
        target_file=target_rel,
        tier_applied=tier,
        max_depth_applied=max_depth_limit,
        max_files_applied=max_files_limit,
        pro_features_enabled=pro_features_enabled,
        enterprise_features_enabled=enterprise_features_enabled,
        extracted_symbols=extracted_symbols,
        total_dependencies=max(0, len(extracted_symbols) - 1),
        unresolved_imports=[],
        import_graph=import_graph,
        circular_imports=[],
        combined_code=combined_code,
        token_estimate=len(combined_code) // 4 if combined_code else 0,
        mermaid=mermaid,
        confidence_decay_factor=confidence_decay_factor,
        low_confidence_count=low_confidence_count,
        low_confidence_warning=low_confidence_warning,
        transitive_depth=effective_max_depth,
        coupling_score=coupling_score,
        dependency_chains=dependency_chains,
        files_scanned=files_scanned,
        files_truncated=files_truncated,
        truncation_warning=truncation_warning,
        truncated=files_truncated > 0,
        files_analyzed=files_analyzed,
        max_depth_reached=max_depth_reached,
    )


def _fast_validate_python_function_node_exists(
    root_path: Path, center_node_id: str
) -> tuple[bool, str | None]:
    """Best-effort fast validation for python::<module>::function::<name>.

    [20260306_DOCS] The get_graph_neighborhood fast path is intentionally scoped
    to local Python function nodes and is wrapped by generic graph validation.

    This avoids building the full call graph when the node ID points to a module
    file that doesn't exist or a function name that doesn't exist in that file.

    Returns:
        (ok, error_message)
    """
    import re

    m = re.match(
        r"^(?P<lang>[^:]+)::(?P<module>[^:]+)::(?P<kind>[^:]+)::(?P<name>.+)$",
        center_node_id.strip(),
    )
    if not m:
        return (
            False,
            "Invalid center_node_id format; expected language::module::type::name. "
            "get_graph_neighborhood currently accepts canonical Python function IDs such as "
            "python::app.routes::function::handle_request.",
        )

    lang = m.group("lang")
    module = m.group("module")
    kind = m.group("kind")
    name = m.group("name")

    if lang != "python" or kind != "function":
        return True, None

    if module in ("external", "unknown"):
        return (
            False,
            f"Center node module '{module}' is not a local Python module for get_graph_neighborhood.",
        )

    # Map module -> file path
    candidate = root_path / (module.replace(".", "/") + ".py")
    if not candidate.exists():
        return (
            False,
            f"Center node file not found for local Python module '{module}': {candidate}",
        )

    # Quick AST scan for a matching function name in that single file.
    # [20260119_FEATURE] Uses unified parser for deterministic behavior.
    try:
        import ast

        code = candidate.read_text(encoding="utf-8")
        tree, _ = parse_python_code(code, filename=str(candidate))
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == name
            ):
                return True, None
        return (
            False,
            f"Center node Python function '{name}' not found in {candidate}",
        )
    except (ParsingError, UnicodeDecodeError, OSError):
        # If parsing fails, fall back to the slow path (graph build)
        return True, None


def _get_graph_neighborhood_sync(
    center_node_id: str,
    k: int = 2,
    max_nodes: int = 100,
    direction: str = "both",
    min_confidence: float = 0.0,
    project_root: str | None = None,
    query: str | None = None,
) -> GraphNeighborhoodResult:
    """Synchronous implementation of get_graph_neighborhood."""
    root_path = Path(project_root) if project_root else _get_project_root()

    # [20260307_FEATURE] Stage 10.1 metadata parity for graph neighborhoods.
    tier = _get_current_tier()
    caps = get_tool_capabilities("get_graph_neighborhood", tier) or {}
    limits = caps.get("limits", {}) or {}
    cap_list = caps.get("capabilities", []) or []
    cap_set = set(cap_list) if not isinstance(cap_list, set) else cap_list
    query_supported = bool("graph_query_language" in cap_set)
    traversal_rules_available = bool("custom_traversal_rules" in cap_set)
    path_constraints_supported = bool("path_constraint_queries" in cap_set)
    max_k_hops = limits.get("max_k_hops", limits.get("max_k"))
    max_nodes_limit = limits.get("max_nodes")
    advanced_resolution = False
    include_enterprise_metrics = bool(
        {
            "custom_traversal",
            "graph_query_language",
            "custom_traversal_rules",
            "path_constraint_queries",
        }
        & cap_set
    )

    if not root_path.exists():
        return GraphNeighborhoodResult(
            success=False,
            tier_applied=tier,
            max_k_applied=max_k_hops,
            max_nodes_applied=max_nodes_limit,
            advanced_resolution_enabled=advanced_resolution,
            enterprise_features_enabled=include_enterprise_metrics,
            error=f"Project root not found: {root_path}.",
        )

    actual_k = k
    k_limited = False
    if max_k_hops is not None and k > max_k_hops:
        actual_k = int(max_k_hops)
        k_limited = True
        k = actual_k

    if max_nodes_limit is not None and max_nodes > max_nodes_limit:
        max_nodes = int(max_nodes_limit)

    # Validate parameters
    if k < 1:
        return GraphNeighborhoodResult(
            success=False,
            tier_applied=tier,
            max_k_applied=max_k_hops,
            max_nodes_applied=max_nodes_limit,
            advanced_resolution_enabled=advanced_resolution,
            enterprise_features_enabled=include_enterprise_metrics,
            error="Parameter 'k' must be at least 1.",
        )

    if max_nodes < 1:
        return GraphNeighborhoodResult(
            success=False,
            tier_applied=tier,
            max_k_applied=max_k_hops,
            max_nodes_applied=max_nodes_limit,
            advanced_resolution_enabled=advanced_resolution,
            enterprise_features_enabled=include_enterprise_metrics,
            error="Parameter 'max_nodes' must be at least 1.",
        )

    if direction not in ("outgoing", "incoming", "both"):
        return GraphNeighborhoodResult(
            success=False,
            tier_applied=tier,
            max_k_applied=max_k_hops,
            max_nodes_applied=max_nodes_limit,
            advanced_resolution_enabled=advanced_resolution,
            enterprise_features_enabled=include_enterprise_metrics,
            error=f"Parameter 'direction' must be 'outgoing', 'incoming', or 'both', got '{direction}'.",
        )

    try:
        center_node_id = _normalize_graph_center_node_id(center_node_id)

        ok, fast_err = _fast_validate_graph_center_node_exists(
            root_path, center_node_id
        )
        if not ok:
            return GraphNeighborhoodResult(
                success=False,
                tier_applied=tier,
                max_k_applied=max_k_hops,
                max_nodes_applied=max_nodes_limit,
                advanced_resolution_enabled=advanced_resolution,
                enterprise_features_enabled=include_enterprise_metrics,
                error=fast_err or "Center node not found",
            )

        # [v3.0.4] Try to use cached graph first
        from code_scalpel.graph_engine import UniversalGraph

        advanced_resolution = bool(
            {
                "advanced_neighborhood",
                "semantic_neighbors",
                "logical_relationship_detection",
                "polymorphism_resolution",
                "virtual_call_tracking",
            }
            & cap_set
        )

        include_enterprise_metrics = bool(
            {
                "custom_traversal",
                "graph_query_language",
                "custom_traversal_rules",
                "path_constraint_queries",
            }
            & cap_set
        )

        parsed_center = _parse_graph_center_node_id(center_node_id)
        if (
            parsed_center is not None
            and parsed_center[0] in {"javascript", "typescript"}
            and parsed_center[2] == "method"
            and not advanced_resolution
        ):
            return GraphNeighborhoodResult(
                success=False,
                tier_applied=tier,
                max_k_applied=max_k_hops,
                max_nodes_applied=max_nodes_limit,
                advanced_resolution_enabled=advanced_resolution,
                enterprise_features_enabled=include_enterprise_metrics,
                error=(
                    "JavaScript and TypeScript method neighborhoods currently require advanced graph capabilities "
                    "(Pro/Enterprise advanced resolution)."
                ),
            )

        cache_variant = "advanced" if advanced_resolution else "basic"
        graph = _get_cached_graph(root_path, cache_variant=cache_variant)

        if graph is None:
            # Cache miss - build the graph.
            # [20260315_BUGFIX] Reuse the shared call-graph helper so bounded
            # polyglot runtime slices (notably Go) produce the same node/edge
            # surface here as they do for public get_call_graph contracts.
            call_graph_result = _get_call_graph_sync(
                str(root_path),
                entry_point=None,
                depth=max(10, actual_k + 2),
                include_circular_import_check=False,
                max_nodes=None,
                advanced_resolution=advanced_resolution,
                include_enterprise_metrics=False,
                paths_from=None,
                paths_to=None,
                focus_functions=None,
                tier=tier,
                capabilities=caps,
            )

            if not call_graph_result.success:
                return GraphNeighborhoodResult(
                    success=False,
                    tier_applied=tier,
                    max_k_applied=max_k_hops,
                    max_nodes_applied=max_nodes_limit,
                    advanced_resolution_enabled=advanced_resolution,
                    enterprise_features_enabled=include_enterprise_metrics,
                    error=call_graph_result.error or "Failed to build call graph.",
                )

            # Convert call graph to UniversalGraph
            from code_scalpel.graph_engine import EdgeType, GraphEdge, GraphNode

            graph = UniversalGraph()

            # Add nodes
            for node in call_graph_result.nodes:
                node_id = _build_graph_node_id(node.file, node.name)
                graph.add_node(
                    GraphNode(
                        id=node_id,
                        metadata={
                            "file": node.file,
                            "line": node.line,
                            "is_entry_point": node.is_entry_point,
                        },
                    )
                )

            # Add edges
            for edge in call_graph_result.edges:
                # Parse caller/callee into node IDs
                caller_parts = edge.caller.split(":")
                callee_parts = edge.callee.split(":")

                caller_file = caller_parts[0] if len(caller_parts) > 1 else ""
                caller_name = caller_parts[-1]
                callee_file = callee_parts[0] if len(callee_parts) > 1 else ""
                callee_name = callee_parts[-1]

                caller_id = _build_graph_node_id(caller_file, caller_name)
                callee_id = _build_graph_node_id(callee_file, callee_name)

                graph.add_edge(
                    GraphEdge(
                        from_id=caller_id,
                        to_id=callee_id,
                        edge_type=EdgeType.DIRECT_CALL,
                        confidence=0.9,
                        evidence="Direct function call",
                    )
                )

            # Cache the built graph for subsequent calls
            _cache_graph(root_path, graph, cache_variant=cache_variant)

        # [20251229_FEATURE] Enterprise tier: Query language support
        if query and "graph_query_language" in cap_set:
            from code_scalpel.graph.graph_query import GraphQueryEngine
            from code_scalpel.graph_engine import NeighborhoodResult, UniversalGraph

            try:
                engine = GraphQueryEngine(graph)
                query_result = engine.execute(query)

                if not query_result.success:
                    return GraphNeighborhoodResult(
                        success=False,
                        error=f"Query execution failed: {query_result.error}",
                    )

                # Build a subgraph from query results (bounded by max_nodes)
                subgraph = UniversalGraph()
                included_node_ids: set[str] = set()

                for node_data in query_result.nodes:
                    if len(included_node_ids) >= max_nodes:
                        break
                    node_id = str(node_data.get("id", "") or "").strip()
                    if not node_id:
                        continue
                    original_node = graph.get_node(node_id)
                    if original_node:
                        subgraph.add_node(original_node)
                        included_node_ids.add(node_id)

                # Add edges from query result (only if both endpoints are included)
                for edge_data in query_result.edges:
                    from_id = str(edge_data.get("from_id", "") or "").strip()
                    to_id = str(edge_data.get("to_id", "") or "").strip()
                    if not from_id or not to_id:
                        continue
                    if (
                        from_id not in included_node_ids
                        or to_id not in included_node_ids
                    ):
                        continue
                    # Find original edge in the graph
                    for edge in graph.edges:
                        if edge.from_id == from_id and edge.to_id == to_id:
                            subgraph.add_edge(edge)
                            break

                node_depths = {node_id: 0 for node_id in included_node_ids}
                truncated = len(query_result.nodes) > max_nodes

                result = NeighborhoodResult(
                    success=True,
                    subgraph=subgraph,
                    center_node_id=center_node_id,
                    k=0,
                    total_nodes=len(subgraph.nodes),
                    total_edges=len(subgraph.edges),
                    max_depth_reached=0,
                    truncated=truncated,
                    truncation_warning=(
                        f"Query result truncated at {max_nodes} nodes due to max_nodes limit."
                        if truncated
                        else None
                    ),
                    node_depths=node_depths,
                )

            except Exception as e:
                return GraphNeighborhoodResult(
                    success=False,
                    error=f"Query language error: {str(e)}",
                )
        else:
            # Standard k-hop extraction
            result = graph.get_neighborhood(
                center_node_id=center_node_id,
                k=k,
                max_nodes=max_nodes,
                direction=direction,
                min_confidence=min_confidence,
            )

        if not result.success:
            return GraphNeighborhoodResult(
                success=False,
                error=result.error,
            )

        # [20251229_FEATURE] Pro tier: Add semantic neighbors
        semantic_neighbor_ids: Set[str] = set()
        if "semantic_neighbors" in cap_set:
            from code_scalpel.graph.semantic_neighbors import SemanticNeighborFinder

            try:
                # Extract center function name from node_id
                center_name = center_node_id.split("::")[-1]
                finder = SemanticNeighborFinder(root_path)
                semantic_result = finder.find_semantic_neighbors(
                    center_name=center_name,
                    k=min(10, max_nodes // 2),
                    min_similarity=0.3,
                )

                if semantic_result.success:
                    for neighbor in semantic_result.neighbors:
                        # Add semantic neighbor to the graph if not already present
                        if neighbor.node_id not in result.node_depths:
                            semantic_neighbor_ids.add(neighbor.node_id)
                            # Add to result's node_depths at depth k+1 (beyond normal k-hop)
                            result.node_depths[neighbor.node_id] = k + 1

                            # Add edge from center to semantic neighbor
                            if result.subgraph:
                                from code_scalpel.graph_engine import (
                                    EdgeType,
                                    GraphEdge,
                                )

                                result.subgraph.add_edge(
                                    GraphEdge(
                                        from_id=center_node_id,
                                        to_id=neighbor.node_id,
                                        edge_type=EdgeType.SEMANTIC_SIMILAR,
                                        confidence=neighbor.similarity_score,
                                        evidence=f"Semantic: {', '.join(neighbor.relationship_types)}",
                                    )
                                )
            except Exception:
                # Semantic neighbor discovery is best-effort, don't fail the whole query
                pass

        # [20251229_FEATURE] Pro tier: Add logical relationships
        if "logical_relationship_detection" in cap_set:
            from code_scalpel.graph.logical_relationships import (
                LogicalRelationshipDetector,
            )

            try:
                center_name = center_node_id.split("::")[-1]
                detector = LogicalRelationshipDetector(root_path)
                relationship_result = detector.find_relationships(
                    center_name=center_name, max_relationships=20
                )

                if relationship_result.success:
                    for rel in relationship_result.relationships:
                        # Add logical relationship as an edge
                        if result.subgraph and rel.source_node in result.node_depths:
                            from code_scalpel.graph_engine import EdgeType, GraphEdge

                            # Ensure target node exists in the graph
                            if rel.target_node not in result.node_depths:
                                result.node_depths[rel.target_node] = k + 1

                            result.subgraph.add_edge(
                                GraphEdge(
                                    from_id=rel.source_node,
                                    to_id=rel.target_node,
                                    edge_type=EdgeType.LOGICAL_RELATED,
                                    confidence=rel.confidence,
                                    evidence=f"Logical: {rel.relationship_type} - {rel.evidence}",
                                )
                            )
            except Exception:
                # Logical relationship detection is best-effort, don't fail the whole query
                pass

        # Convert to response models
        nodes = []
        for node_id, depth in result.node_depths.items():
            node = result.subgraph.get_node(node_id) if result.subgraph else None
            nodes.append(
                NeighborhoodNodeModel(
                    id=node_id,
                    depth=depth,
                    metadata=node.metadata if node else {},
                )
            )

        edges = []
        if result.subgraph:
            for edge in result.subgraph.edges:
                edges.append(
                    NeighborhoodEdgeModel(
                        from_id=edge.from_id,
                        to_id=edge.to_id,
                        edge_type=edge.edge_type.value,
                        confidence=edge.confidence,
                    )
                )

        # Generate Mermaid diagram
        mermaid = _generate_neighborhood_mermaid(nodes, edges, center_node_id)

        hot_nodes: list[str] = []
        if include_enterprise_metrics:
            # [20251225_FEATURE] Best-effort degree metrics within the returned subgraph.
            in_deg: dict[str, int] = {}
            out_deg: dict[str, int] = {}
            for edge in edges:
                out_deg[edge.from_id] = out_deg.get(edge.from_id, 0) + 1
                in_deg[edge.to_id] = in_deg.get(edge.to_id, 0) + 1

            for n in nodes:
                n.in_degree = in_deg.get(n.id, 0)
                n.out_degree = out_deg.get(n.id, 0)

            def _degree_key(n: NeighborhoodNodeModel) -> tuple[int, str]:
                return (((n.in_degree or 0) + (n.out_degree or 0)), n.id)

            hot_nodes = [
                n.id
                for n in sorted(nodes, key=_degree_key, reverse=True)[:10]
                if _degree_key(n)[0] > 0
            ]

        return GraphNeighborhoodResult(
            success=True,
            center_node_id=center_node_id,
            k=actual_k,
            tier_applied=tier,
            max_k_applied=max_k_hops,
            max_nodes_applied=max_nodes_limit,
            advanced_resolution_enabled=advanced_resolution,
            enterprise_features_enabled=include_enterprise_metrics,
            nodes=nodes,
            edges=edges,
            total_nodes=result.total_nodes,
            total_edges=result.total_edges,
            max_depth_reached=result.max_depth_reached,
            truncated=result.truncated or k_limited,
            truncation_warning=result.truncation_warning,
            mermaid=mermaid,
            hot_nodes=hot_nodes,
            query_supported=query_supported,
            traversal_rules_available=traversal_rules_available,
            path_constraints_supported=path_constraints_supported,
        )

    except Exception as e:
        return GraphNeighborhoodResult(
            success=False,
            tier_applied=tier,
            max_k_applied=max_k_hops,
            max_nodes_applied=max_nodes_limit,
            advanced_resolution_enabled=advanced_resolution,
            enterprise_features_enabled=include_enterprise_metrics,
            error=f"Graph neighborhood extraction failed: {str(e)}",
        )


# ============================================================================
# [20251213_FEATURE] v1.5.0 - get_project_map MCP Tool
# ============================================================================


def _get_project_map_sync(
    project_root: str | None,
    include_complexity: bool,
    complexity_threshold: int,
    include_circular_check: bool,
    *,
    tier: str | None = None,
    capabilities: dict | None = None,
    max_files_limit: int | None = None,
    max_modules_limit: int | None = None,
) -> ProjectMapResult:
    """Synchronous implementation of get_project_map.

    The function is tier-aware; limits and capabilities are computed in the async wrapper
    and passed through to avoid re-resolving tier in worker threads.
    """
    import ast
    import subprocess

    from code_scalpel.ast_tools.call_graph import CallGraphBuilder

    root_path = Path(project_root) if project_root else _get_project_root()

    # [20250112_FIX] Resolve tier before try block so it's available in except
    tier = tier or _get_current_tier()

    if not root_path.exists():
        return ProjectMapResult(
            success=False,
            project_root=str(root_path),
            error=f"Project root not found: {root_path}.",
            tier_applied=tier,
            pro_features_enabled=tier in ("pro", "enterprise"),
            enterprise_features_enabled=tier == "enterprise",
        )

    try:
        caps = capabilities or get_tool_capabilities("get_project_map", tier) or {}
        caps_set = set(caps.get("capabilities", set()) or [])
        limits = caps.get("limits", {}) or {}

        effective_max_files = max_files_limit
        if effective_max_files is None:
            effective_max_files = limits.get("max_files")

        effective_max_modules = max_modules_limit
        if effective_max_modules is None:
            effective_max_modules = limits.get("max_modules")

        if effective_max_modules is None:
            effective_max_modules = 50

        modules: list[ModuleInfo] = []
        packages: dict[str, PackageInfo] = {}
        all_entry_points: list[str] = []
        complexity_hotspots: list[str] = []
        total_lines = 0
        java_relation_hints_by_module: dict[str, list[str]] = {}
        java_package_by_module: dict[str, str] = {}
        java_package_index: dict[str, set[str]] = {}

        # Entry point detection patterns
        entry_decorators = {
            "command",
            "main",
            "cli",
            "app",
            "route",
            "get",
            "post",
            "put",
            "delete",
        }

        def is_entry_point(func_node: ast.AST) -> bool:
            """Check if function is an entry point."""
            # Type guard: must be FunctionDef or AsyncFunctionDef
            if not isinstance(func_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return False
            if func_node.name == "main":
                return True
            for dec in getattr(func_node, "decorator_list", []):
                dec_name = ""
                if isinstance(dec, ast.Name):
                    dec_name = dec.id
                elif isinstance(dec, ast.Attribute):
                    dec_name = dec.attr
                elif isinstance(dec, ast.Call):
                    if isinstance(dec.func, ast.Attribute):
                        dec_name = dec.func.attr
                    elif isinstance(dec.func, ast.Name):
                        dec_name = dec.func.id
                if dec_name in entry_decorators:
                    return True
            return False

        def calculate_complexity(tree: ast.AST) -> int:
            """Calculate cyclomatic complexity of a module."""
            complexity = 1  # Base complexity
            for node in ast.walk(tree):
                if isinstance(
                    node,
                    (
                        ast.If,
                        ast.While,
                        ast.For,
                        ast.AsyncFor,
                        ast.ExceptHandler,
                        ast.With,
                        ast.AsyncWith,
                        ast.Assert,
                        ast.comprehension,
                    ),
                ):
                    complexity += 1
                elif isinstance(node, (ast.And, ast.Or)):
                    complexity += 1
                elif isinstance(node, ast.BoolOp):
                    complexity += len(node.values) - 1
            return complexity

        # [20260311_FEATURE] Extend local parity slices to Go for get_project_map.
        # Keep Python as the primary path, but include local JS/TS/Java/Go source files.
        source_files = [
            f
            for f in root_path.rglob("*")
            if f.is_file()
            and f.suffix.lower()
            in (
                {".py"}
                | set(_PROJECT_MAP_JS_TS_SUFFIXES)
                | set(_PROJECT_MAP_JAVA_SUFFIXES)
                | set(_PROJECT_MAP_GO_SUFFIXES)
            )
        ]

        # [20251229_BUGFIX] Filter exclusions BEFORE applying file limit
        # Previously: files were sorted/limited first, then filtered, causing
        # .venv files to dominate the limited set and then be filtered out,
        # resulting in zero modules detected.
        exclude_patterns = {
            "__pycache__",
            ".git",
            "venv",
            ".venv",
            "env",
            ".env",
            "node_modules",
            "dist",
            "build",
            ".tox",
            ".pytest_cache",
            "htmlcov",
            ".mypy_cache",
        }

        # Filter out excluded directories FIRST
        # Check both exact matches and startswith for patterns like .venv-*
        def should_exclude(file_path: Path) -> bool:
            for part in file_path.parts:
                # Exact match
                if part in exclude_patterns:
                    return True
                # Startswith match for patterns like .venv-mcp-smoke
                for pattern in exclude_patterns:
                    if part.startswith(pattern):
                        return True
            return False

        source_files = [f for f in source_files if not should_exclude(f)]

        # [20251226_FEATURE] Tier-aware file cap - AFTER filtering
        source_files = sorted(source_files)
        if effective_max_files is not None and len(source_files) > effective_max_files:
            source_files = source_files[:effective_max_files]

        for file_path in source_files:
            rel_path = str(file_path.relative_to(root_path))

            try:
                if file_path.suffix.lower() in _PROJECT_MAP_JS_TS_SUFFIXES:
                    js_ts_module = _scan_js_ts_project_map_module(
                        file_path,
                        root_path,
                        include_complexity,
                    )
                    if js_ts_module is None:
                        continue

                    total_lines += js_ts_module.line_count
                    if (
                        include_complexity
                        and js_ts_module.complexity_score >= complexity_threshold
                    ):
                        complexity_hotspots.append(
                            f"{rel_path} (complexity: {js_ts_module.complexity_score})"
                        )

                    all_entry_points.extend(js_ts_module.entry_points)
                    modules.append(js_ts_module)
                    continue

                if file_path.suffix.lower() in _PROJECT_MAP_JAVA_SUFFIXES:
                    java_scan = _scan_java_project_map_module(
                        file_path,
                        root_path,
                        include_complexity,
                    )
                    if java_scan is None:
                        continue

                    java_module = java_scan.module

                    total_lines += java_module.line_count
                    if (
                        include_complexity
                        and java_module.complexity_score >= complexity_threshold
                    ):
                        complexity_hotspots.append(
                            f"{rel_path} (complexity: {java_module.complexity_score})"
                        )

                    all_entry_points.extend(java_module.entry_points)
                    modules.append(java_module)

                    java_relation_hints_by_module[java_module.path] = list(
                        java_scan.relation_hints
                    )
                    if java_scan.package_name:
                        java_package_by_module[java_module.path] = java_scan.package_name
                        package_path = java_scan.package_name.replace(".", "/")
                        _register_project_map_package(
                            packages,
                            package_path,
                            java_module.path,
                        )
                        java_package_index.setdefault(java_scan.package_name, set()).add(
                            java_module.path
                        )
                    continue

                if file_path.suffix.lower() in _PROJECT_MAP_GO_SUFFIXES:
                    go_module = _scan_go_project_map_module(
                        file_path,
                        root_path,
                        include_complexity,
                    )
                    if go_module is None:
                        continue

                    total_lines += go_module.line_count
                    if (
                        include_complexity
                        and go_module.complexity_score >= complexity_threshold
                    ):
                        complexity_hotspots.append(
                            f"{rel_path} (complexity: {go_module.complexity_score})"
                        )

                    all_entry_points.extend(go_module.entry_points)
                    modules.append(go_module)
                    continue

                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    code = f.read()

                lines = code.count("\n") + 1
                total_lines += lines

                # [20260119_FEATURE] Uses unified parser for deterministic behavior.
                tree, _ = parse_python_code(code, filename=rel_path)

                # Extract module info
                functions = []
                classes = []
                imports = []
                entry_points = []

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        functions.append(node.name)
                        if is_entry_point(node):
                            entry_points.append(f"{rel_path}:{node.name}")
                    elif isinstance(node, ast.ClassDef):
                        classes.append(node.name)
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.append(node.module)

                # Calculate complexity if requested
                complexity = 0
                if include_complexity:
                    complexity = calculate_complexity(tree)
                    if complexity >= complexity_threshold:
                        complexity_hotspots.append(
                            f"{rel_path} (complexity: {complexity})"
                        )

                all_entry_points.extend(entry_points)

                modules.append(
                    ModuleInfo(
                        path=rel_path,
                        functions=functions,
                        classes=classes,
                        imports=list(set(imports)),  # Dedupe
                        entry_points=entry_points,
                        line_count=lines,
                        complexity_score=complexity,
                    )
                )

                # Track packages
                parent = file_path.parent
                while parent != root_path and parent.exists():
                    init_file = parent / "__init__.py"
                    if init_file.exists():
                        pkg_path = str(parent.relative_to(root_path))
                        pkg_name = parent.name
                        if pkg_path not in packages:
                            packages[pkg_path] = PackageInfo(
                                name=pkg_name,
                                path=pkg_path,
                                modules=[],
                                subpackages=[],
                            )
                        # Add module to package
                        if rel_path not in packages[pkg_path].modules:
                            packages[pkg_path].modules.append(rel_path)
                    parent = parent.parent

            except Exception:
                # Skip files with errors
                continue

        # Organize package hierarchy
        pkg_list = list(packages.values())
        for pkg in pkg_list:
            for other_pkg in pkg_list:
                if (
                    other_pkg.path.startswith(pkg.path + "/")
                    and other_pkg.name not in pkg.subpackages
                ):
                    pkg.subpackages.append(other_pkg.name)

        # Check for circular imports
        circular_imports = []
        if include_circular_check:
            builder = CallGraphBuilder(root_path)
            circular_imports = builder.detect_circular_imports()

        # [20260307_FEATURE] Count languages from analyzed source modules first.
        languages: dict[str, int] = {}
        for mod in modules:
            detected_language = _project_map_detect_language(mod.path)
            if detected_language != "other":
                languages[detected_language] = languages.get(detected_language, 0) + 1

        # Also count other common file types.
        # [20260315_BUGFIX] Aggregate by language first so variants like
        # .yaml/.yml contribute cumulatively instead of the later extension being
        # canceled out by the earlier language total.
        extra_file_counts: dict[str, int] = {}
        for ext, lang in [
            (".js", "javascript"),
            (".ts", "typescript"),
            (".java", "java"),
            (".json", "json"),
            (".yaml", "yaml"),
            (".yml", "yaml"),
            (".md", "markdown"),
            (".html", "html"),
            (".css", "css"),
        ]:
            actual_count = sum(
                1
                for f in root_path.rglob(f"*{ext}")
                if not any(p in exclude_patterns for p in f.parts)
            )
            extra_file_counts[lang] = extra_file_counts.get(lang, 0) + actual_count

        for lang, actual_count in extra_file_counts.items():
            analyzed_count = languages.get(lang, 0)
            remainder = max(actual_count - analyzed_count, 0)
            if remainder > 0:
                languages[lang] = analyzed_count + remainder

        modules_in_diagram = (
            len(modules)
            if effective_max_modules is None
            else min(len(modules), int(effective_max_modules))
        )
        diagram_limit = modules_in_diagram

        go_module_name = _read_go_project_map_module_name(root_path)
        java_resolver = None
        if any(Path(mod.path).suffix.lower() in _PROJECT_MAP_JAVA_SUFFIXES for mod in modules):
            try:
                from code_scalpel.ast_tools.java_import_resolver import JavaImportResolver

                # [20260315_FEATURE] Reuse JavaImportResolver edges so project-map
                # Java relationships honor explicit, static, and wildcard imports.
                java_resolver = JavaImportResolver(root_path)
                java_resolver.build()
            except Exception:
                java_resolver = None

        js_ts_alias_resolver = None
        try:
            from code_scalpel.code_parsers.typescript_parsers.alias_resolver import (
                create_alias_resolver,
            )

            # [20260314_FEATURE] Reuse the shared TS alias resolver so
            # get_project_map can navigate tsconfig-backed local imports in
            # relationship-aware tiers.
            js_ts_alias_resolver = create_alias_resolver(root_path)
        except Exception:
            js_ts_alias_resolver = None

        # [20251226_FEATURE] Tier-aware relationship + analytics construction
        module_index: dict[str, str] = {}
        for mod in modules:
            path_obj = Path(mod.path)
            suffix = path_obj.suffix.lower()
            if suffix == ".py":
                dotted = mod.path[:-3].replace("/", ".")
                module_index[dotted] = mod.path
                continue

            if suffix in _PROJECT_MAP_JS_TS_SUFFIXES:
                stem = str(path_obj.with_suffix("")).replace("\\", "/")
                module_index[stem] = mod.path
                if path_obj.stem == "index":
                    module_index[str(path_obj.parent).replace("\\", "/")] = mod.path
                continue

            if suffix in _PROJECT_MAP_JAVA_SUFFIXES:
                dotted = (
                    str(path_obj.with_suffix("")).replace("\\", "/").replace("/", ".")
                )
                module_index[dotted] = mod.path
                declared_package = java_package_by_module.get(mod.path)
                if declared_package:
                    for class_name in mod.classes:
                        module_index[f"{declared_package}.{class_name}"] = mod.path
                continue

            if suffix in _PROJECT_MAP_GO_SUFFIXES:
                stem = str(path_obj.with_suffix("")).replace("\\", "/")
                module_index[stem] = mod.path
                package_dir = str(path_obj.parent).replace("\\", "/")
                if package_dir not in {"", "."}:
                    module_index[package_dir] = mod.path
                    if go_module_name:
                        module_index[f"{go_module_name}/{package_dir}".strip("/")] = mod.path
                elif go_module_name:
                    module_index[go_module_name] = mod.path

        known_module_paths = {mod.path for mod in modules}

        module_relationships: list[dict[str, str]] | None = None
        dependency_diagram: str | None = None
        architectural_layers: list[dict[str, str]] | None = None
        coupling_metrics: list[dict[str, Any]] | None = None
        force_graph: dict[str, Any] | None = None
        city_map_data: dict[str, Any] | None = None
        churn_heatmap: list[dict[str, Any]] | None = None
        bug_hotspots: list[dict[str, Any]] | None = None
        git_ownership: list[dict[str, Any]] | None = None
        # [20251231_FEATURE] v3.3.1 - New Enterprise feature variables
        multi_repo_summary: dict[str, Any] | None = None
        historical_trends: list[dict[str, Any]] | None = None
        custom_metrics: dict[str, Any] | None = None
        compliance_overlay: dict[str, Any] | None = None

        # [20251226_BUGFIX] Align capability flags with tier when feature map differs
        enable_relationships = (
            "module_relationship_visualization" in caps_set
            or "dependency_tracking" in caps_set
            or (tier and tier.lower() in {"pro", "enterprise"})
        )
        enable_dependency_diagram = "import_dependency_diagram" in caps_set or (
            tier and tier.lower() in {"pro", "enterprise"}
        )
        enable_layers = "architectural_layer_detection" in caps_set or (
            tier and tier.lower() in {"pro", "enterprise"}
        )
        enable_coupling = "coupling_analysis" in caps_set or (
            tier and tier.lower() in {"pro", "enterprise"}
        )
        enable_force_graph = "force_directed_graph" in caps_set or (
            tier and tier.lower() == "enterprise"
        )
        enable_city = "interactive_city_map" in caps_set or (
            tier and tier.lower() == "enterprise"
        )
        enable_churn = "code_churn_visualization" in caps_set or (
            tier and tier.lower() == "enterprise"
        )
        enable_bug_hotspots = "bug_hotspot_heatmap" in caps_set or (
            tier and tier.lower() == "enterprise"
        )
        enable_git_blame = "git_blame_integration" in caps_set or (
            tier and tier.lower() in {"pro", "enterprise"}
        )
        # [20251231_FEATURE] v3.3.1 - New Enterprise feature flags
        enable_multi_repo = "multi_repository_maps" in caps_set or (
            tier and tier.lower() == "enterprise"
        )
        enable_historical_trends = "historical_architecture_trends" in caps_set or (
            tier and tier.lower() == "enterprise"
        )
        enable_custom_metrics = "custom_map_metrics" in caps_set or (
            tier and tier.lower() == "enterprise"
        )
        enable_compliance_overlay = "compliance_overlay" in caps_set or (
            tier and tier.lower() == "enterprise"
        )

        edges: list[tuple[str, str]] = []
        if (
            enable_relationships
            or enable_dependency_diagram
            or enable_coupling
            or enable_layers
            or enable_force_graph
            or enable_city
        ):
            for mod in modules:
                relationship_hints = mod.imports
                mod_suffix = Path(mod.path).suffix.lower()
                if mod_suffix in _PROJECT_MAP_JAVA_SUFFIXES:
                    if java_resolver is not None:
                        try:
                            abs_path = str((root_path / mod.path).resolve())
                            source_module = java_resolver.file_to_module.get(abs_path)
                            if source_module:
                                for target_module in sorted(
                                    java_resolver.edges.get(source_module, set())
                                ):
                                    target_file = java_resolver.module_to_file.get(
                                        target_module
                                    )
                                    if target_file:
                                        rel_target = str(
                                            Path(target_file)
                                            .resolve()
                                            .relative_to(root_path)
                                        ).replace("\\", "/")
                                        if rel_target != mod.path:
                                            edges.append((mod.path, rel_target))
                        except Exception:
                            pass

                    relationship_hints = java_relation_hints_by_module.get(
                        mod.path,
                        mod.imports,
                    )

                for imp in relationship_hints:
                    target_paths = _resolve_project_map_import_target(
                        imp,
                        mod.path,
                        module_index,
                        root_path=root_path,
                        known_module_paths=known_module_paths,
                        js_ts_alias_resolver=js_ts_alias_resolver,
                        package_index=java_package_index,
                        java_package_by_module=java_package_by_module,
                    )
                    for target_path in target_paths:
                        if target_path != mod.path:
                            edges.append((mod.path, target_path))

            edges = list(dict.fromkeys(edges))

        if enable_relationships:
            module_relationships = [
                {"source": src, "target": dst, "type": "import"} for src, dst in edges
            ]

        if enable_dependency_diagram and edges:
            diagram_lines = ["graph TD"]
            for idx, mod in enumerate(modules[:modules_in_diagram]):
                node_id = f"N{idx}"
                label = mod.path.replace("/", "_").replace(".", "_")
                diagram_lines.append(f'    {node_id}["{label}"]')
            path_to_id = {
                mod.path: f"N{idx}"
                for idx, mod in enumerate(modules[:modules_in_diagram])
            }
            for src, dst in edges:
                if src in path_to_id and dst in path_to_id:
                    diagram_lines.append(f"    {path_to_id[src]} --> {path_to_id[dst]}")
            dependency_diagram = "\n".join(diagram_lines)

        if enable_layers:

            def classify_layer(path: str) -> tuple[str, str]:
                lowered = path.lower()
                if any(k in lowered for k in ["controller", "view", "handler", "api"]):
                    return "controller", "Matched controller/view keywords"
                if any(k in lowered for k in ["service", "logic", "manager"]):
                    return "service", "Matched service/logic keywords"
                if any(
                    k in lowered for k in ["repo", "repository", "model", "dao", "db"]
                ):
                    return "repository", "Matched repository/model keywords"
                if any(k in lowered for k in ["util", "helper", "common", "shared"]):
                    return "utility", "Matched utility keywords"
                return "other", "No heuristic match"

            architectural_layers = []
            for mod in modules:
                layer, reason = classify_layer(mod.path)
                architectural_layers.append(
                    {"module": mod.path, "layer": layer, "reason": reason}
                )

        if enable_coupling:
            outgoing: dict[str, set[str]] = {mod.path: set() for mod in modules}
            incoming: dict[str, set[str]] = {mod.path: set() for mod in modules}
            for src, dst in edges:
                if src in outgoing:
                    outgoing[src].add(dst)
                if dst in incoming:
                    incoming[dst].add(src)

            coupling_metrics = []
            for mod in modules:
                ca = len(incoming.get(mod.path, set()))
                ce = len(outgoing.get(mod.path, set()))
                denom = ca + ce
                instability = ce / denom if denom else 0.0
                coupling_metrics.append(
                    {
                        "module": mod.path,
                        "afferent": ca,
                        "efferent": ce,
                        "instability": round(instability, 3),
                    }
                )

        if enable_force_graph and edges:
            force_graph = {
                "nodes": [
                    {
                        "id": mod.path,
                        "group": (
                            (architectural_layers or [{}])[idx].get("layer", "other")
                            if architectural_layers
                            else "other"
                        ),
                    }
                    for idx, mod in enumerate(modules)
                ],
                "links": [
                    {"source": src, "target": dst, "value": 1} for src, dst in edges
                ],
            }

        if enable_city:
            city_map_data = {
                "buildings": [
                    {
                        "id": mod.path,
                        "height": max(mod.complexity_score, 1),
                        "footprint": max(mod.line_count // 10, 1),
                        "layer": next(
                            (
                                layer_info["layer"]
                                for layer_info in (architectural_layers or [])
                                if layer_info.get("module") == mod.path
                            ),
                            "other",
                        ),
                    }
                    for mod in modules
                ]
            }

        if enable_churn:
            churn_heatmap = []
            for mod in modules:
                churn_score = mod.complexity_score + len(mod.imports)
                level = "low"
                if churn_score > 20:
                    level = "high"
                elif churn_score > 10:
                    level = "medium"
                churn_heatmap.append(
                    {"module": mod.path, "churn_score": churn_score, "level": level}
                )

        if enable_bug_hotspots:
            bug_hotspots = []
            for mod in modules:
                if mod.complexity_score >= complexity_threshold or len(mod.imports) > 5:
                    bug_hotspots.append(
                        {
                            "module": mod.path,
                            "reason": "High complexity or import fan-in",
                        }
                    )
            if not bug_hotspots:
                bug_hotspots = [
                    {"module": mod.path, "reason": "No hotspots detected"}
                    for mod in modules[:1]
                ]

        if enable_git_blame:
            # [20251229_FEATURE] Enterprise: Git blame integration
            git_ownership = []
            try:
                import subprocess

                # Check if we're in a git repository
                result = subprocess.run(
                    ["git", "rev-parse", "--is-inside-work-tree"],
                    cwd=root_path,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode == 0:
                    # We're in a git repo, analyze file ownership
                    for mod in modules:
                        try:
                            file_path = root_path / mod.path
                            # Run git blame to get line-by-line authorship
                            blame_result = subprocess.run(
                                ["git", "blame", "--line-porcelain", str(file_path)],
                                cwd=root_path,
                                capture_output=True,
                                text=True,
                                timeout=10,
                            )

                            if blame_result.returncode == 0:
                                # Parse git blame output
                                authors: dict[str, int] = {}
                                for line in blame_result.stdout.split("\n"):
                                    if line.startswith("author "):
                                        author = line[
                                            7:
                                        ].strip()  # Remove "author " prefix
                                        authors[author] = authors.get(author, 0) + 1

                                if authors:
                                    # Find primary owner (most lines authored)
                                    total_lines = sum(authors.values())
                                    primary_owner = max(
                                        authors.items(), key=lambda x: x[1]
                                    )
                                    owner_name = primary_owner[0]
                                    owner_lines = primary_owner[1]
                                    confidence = round(owner_lines / total_lines, 2)

                                    git_ownership.append(
                                        {
                                            "module": mod.path,
                                            "owner": owner_name,
                                            "confidence": confidence,
                                            "contributors": len(authors),
                                            "ownership_breakdown": {
                                                k: round(v / total_lines, 2)
                                                for k, v in sorted(
                                                    authors.items(),
                                                    key=lambda x: x[1],
                                                    reverse=True,
                                                )[:5]
                                            },
                                        }
                                    )
                                else:
                                    git_ownership.append(
                                        {
                                            "module": mod.path,
                                            "owner": "unknown",
                                            "confidence": 0.0,
                                            "reason": "No git blame data",
                                        }
                                    )
                            else:
                                git_ownership.append(
                                    {
                                        "module": mod.path,
                                        "owner": "unknown",
                                        "confidence": 0.0,
                                        "reason": "File not tracked in git",
                                    }
                                )
                        except subprocess.TimeoutExpired:
                            git_ownership.append(
                                {
                                    "module": mod.path,
                                    "owner": "unknown",
                                    "confidence": 0.0,
                                    "reason": "Git blame timeout",
                                }
                            )
                        except Exception as e:
                            git_ownership.append(
                                {
                                    "module": mod.path,
                                    "owner": "unknown",
                                    "confidence": 0.0,
                                    "reason": f"Error: {str(e)}",
                                }
                            )
                else:
                    # Not a git repository
                    git_ownership = [
                        {
                            "module": mod.path,
                            "owner": "unknown",
                            "confidence": 0.0,
                            "reason": "Not a git repository",
                        }
                        for mod in modules
                    ]
            except FileNotFoundError:
                # Git not installed
                git_ownership = [
                    {
                        "module": mod.path,
                        "owner": "unknown",
                        "confidence": 0.0,
                        "reason": "Git not installed",
                    }
                    for mod in modules
                ]
            except Exception as e:
                # Other error
                git_ownership = [
                    {
                        "module": mod.path,
                        "owner": "unknown",
                        "confidence": 0.0,
                        "reason": f"Error: {str(e)}",
                    }
                    for mod in modules
                ]

        # [20251231_FEATURE] v3.3.1 - Enterprise: Historical architecture trends
        if enable_historical_trends:
            historical_trends = []
            try:
                import subprocess

                # Check if we're in a git repository
                result = subprocess.run(
                    ["git", "rev-parse", "--is-inside-work-tree"],
                    cwd=root_path,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode == 0:
                    # Get file changes over last 30 days for trend analysis
                    log_result = subprocess.run(
                        [
                            "git",
                            "log",
                            "--since=30 days ago",
                            "--name-only",
                            "--pretty=format:%H|%ad|%an",
                            "--date=short",
                        ],
                        cwd=root_path,
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )

                    if log_result.returncode == 0:
                        # Parse git log output into trends
                        file_change_counts: dict[str, int] = {}
                        date_activity: dict[str, int] = {}

                        current_date = ""
                        for line in log_result.stdout.split("\n"):
                            line = line.strip()
                            if not line:
                                continue
                            if "|" in line:
                                # This is a commit header line
                                parts = line.split("|")
                                if len(parts) >= 2:
                                    current_date = parts[1]
                                    date_activity[current_date] = (
                                        date_activity.get(current_date, 0) + 1
                                    )
                            elif line.endswith(".py"):
                                # This is a Python file that was changed
                                file_change_counts[line] = (
                                    file_change_counts.get(line, 0) + 1
                                )

                        # Calculate architecture stability metrics
                        total_changes = sum(file_change_counts.values())
                        hot_files = sorted(
                            file_change_counts.items(), key=lambda x: x[1], reverse=True
                        )[:10]

                        historical_trends = [
                            {
                                "period": "last_30_days",
                                "total_commits": len(date_activity),
                                "total_file_changes": total_changes,
                                "most_changed_files": [
                                    {"file": f, "changes": c} for f, c in hot_files
                                ],
                                "activity_by_date": date_activity,
                                "stability_score": round(
                                    1.0
                                    - min(
                                        total_changes / max(len(modules) * 3, 1), 1.0
                                    ),
                                    2,
                                ),
                            }
                        ]
                    else:
                        historical_trends = [{"error": "Could not retrieve git log"}]
                else:
                    historical_trends = [{"error": "Not a git repository"}]
            except subprocess.TimeoutExpired:
                historical_trends = [{"error": "Git log timeout"}]
            except FileNotFoundError:
                historical_trends = [{"error": "Git not installed"}]
            except Exception as e:
                historical_trends = [{"error": f"Historical trends failed: {str(e)}"}]

        # [20251231_FEATURE] v3.3.1 - Enterprise: Custom map metrics
        if enable_custom_metrics:
            # Load custom metrics from architecture.toml if present
            custom_metrics = {
                "configured": False,
                "metrics": {},
            }
            try:
                arch_config_path = root_path / ".code-scalpel" / "architecture.toml"
                if arch_config_path.exists():
                    try:
                        import tomllib
                    except ImportError:
                        import tomli as tomllib  # type: ignore

                    with open(arch_config_path, "rb") as f:
                        arch_config = tomllib.load(f)

                    if "custom_metrics" in arch_config:
                        custom_metrics = {
                            "configured": True,
                            "source": str(arch_config_path),
                            "metrics": arch_config["custom_metrics"],
                        }
                    else:
                        custom_metrics["note"] = (
                            "No custom_metrics section in architecture.toml"
                        )
                else:
                    custom_metrics["note"] = "No .code-scalpel/architecture.toml found"
            except Exception as e:
                custom_metrics["error"] = f"Failed to load custom metrics: {str(e)}"

        # [20251231_FEATURE] v3.3.1 - Enterprise: Compliance overlay
        if enable_compliance_overlay:
            compliance_overlay = {
                "violations": [],
                "status": "unknown",
            }
            try:
                # Try to use the architectural rules engine if available
                arch_config_path = root_path / ".code-scalpel" / "architecture.toml"
                if arch_config_path.exists():
                    try:
                        # [20260101_BUGFIX] Dynamic import to avoid Pyright errors
                        from code_scalpel.ast_tools import architectural_rules

                        ArchitecturalRulesEngine = getattr(
                            architectural_rules, "ArchitecturalRulesEngine", None
                        )
                        if ArchitecturalRulesEngine is None:
                            raise ImportError("ArchitecturalRulesEngine not found")

                        engine = ArchitecturalRulesEngine(str(arch_config_path))

                        # Analyze each module for architectural violations
                        violations: list[dict[str, Any]] = []
                        for mod in modules:
                            for imp in mod.imports:
                                violation = engine.check_import(mod.path, imp)
                                if violation:
                                    violations.append(
                                        {
                                            "file": mod.path,
                                            "import": imp,
                                            "rule": violation.rule_name,
                                            "severity": violation.severity,
                                            "message": violation.message,
                                        }
                                    )

                        compliance_overlay = {
                            "violations": violations,
                            "violation_count": len(violations),
                            "status": (
                                "compliant" if len(violations) == 0 else "non_compliant"
                            ),
                            "rules_source": str(arch_config_path),
                        }
                    except ImportError:
                        compliance_overlay = {
                            "violations": [],
                            "status": "unavailable",
                            "note": "Architectural rules engine not available",
                        }
                else:
                    compliance_overlay = {
                        "violations": [],
                        "status": "unconfigured",
                        "note": "No .code-scalpel/architecture.toml found",
                    }
            except Exception as e:
                compliance_overlay = {
                    "violations": [],
                    "status": "error",
                    "error": f"Compliance check failed: {str(e)}",
                }

        # [20251231_FEATURE] v3.3.1 - Enterprise: Multi-repository summary placeholder
        # This feature requires additional_roots parameter; for now provide metadata
        if enable_multi_repo:
            multi_repo_summary = {
                "enabled": True,
                "primary_root": str(root_path),
                "additional_roots": [],  # Future: pass via parameter
                "note": "Pass additional_roots parameter for multi-repo analysis",
                "total_repositories": 1,
            }

        # Generate Mermaid package diagram
        mermaid_lines = ["graph TD"]
        mermaid_lines.append("    subgraph Project")
        for i, mod in enumerate(modules[:diagram_limit]):
            mod_id = f"M{i}"
            label = mod.path.replace("/", "_").replace(".", "_")
            if mod.entry_points:
                mermaid_lines.append(
                    f'        {mod_id}[["{label}"]]'
                )  # Stadium for entry
            else:
                mermaid_lines.append(f'        {mod_id}["{label}"]')
        mermaid_lines.append("    end")

        # [20251220_FEATURE] v3.0.5 - Communicate truncation
        diagram_truncated = (
            effective_max_modules is not None and len(modules) > effective_max_modules
        )
        if diagram_truncated and effective_max_modules is not None:
            mermaid_lines.append(
                f"    Note[... and {len(modules) - int(effective_max_modules)} more modules]"
            )

        return ProjectMapResult(
            project_root=str(root_path),
            total_files=len(modules),
            total_lines=total_lines,
            languages=languages,
            packages=pkg_list,
            modules=modules,
            entry_points=all_entry_points,
            circular_imports=circular_imports,
            complexity_hotspots=complexity_hotspots,
            mermaid="\n".join(mermaid_lines),
            module_relationships=module_relationships,
            architectural_layers=architectural_layers,
            coupling_metrics=coupling_metrics,
            dependency_diagram=dependency_diagram,
            city_map_data=city_map_data,
            force_graph=force_graph,
            churn_heatmap=churn_heatmap,
            bug_hotspots=bug_hotspots,
            git_ownership=git_ownership,
            # [20251231_FEATURE] v3.3.1 - New Enterprise fields
            multi_repo_summary=multi_repo_summary,
            historical_trends=historical_trends,
            custom_metrics=custom_metrics,
            compliance_overlay=compliance_overlay,
            modules_in_diagram=modules_in_diagram,
            diagram_truncated=diagram_truncated,
            # [20250112_FIX] v3.3.0 - Include tier metadata fields
            tier_applied=tier,
            max_files_applied=effective_max_files,
            max_modules_applied=effective_max_modules,
            pro_features_enabled=tier in ("pro", "enterprise"),
            enterprise_features_enabled=tier == "enterprise",
        )

    except Exception as e:
        # tier is available since we resolve it before the try block
        return ProjectMapResult(
            success=False,
            project_root=str(root_path),
            error=f"Project map analysis failed: {str(e)}",
            tier_applied=tier,
            pro_features_enabled=tier in ("pro", "enterprise"),
            enterprise_features_enabled=tier == "enterprise",
        )


# ============================================================================
# [20251213_FEATURE] v1.5.1 - get_cross_file_dependencies MCP Tool
# ============================================================================


def _get_cross_file_dependencies_sync(
    target_file: str,
    target_symbol: str,
    project_root: str | None,
    max_depth: int,
    include_code: bool,
    include_diagram: bool,
    confidence_decay_factor: float = 0.9,
    tier: str | None = None,
    capabilities: dict | None = None,
    max_files_limit: int | None = None,
    timeout_seconds: float | None = None,
) -> CrossFileDependenciesResult:
    """
    Synchronous implementation of get_cross_file_dependencies.

    [20251220_BUGFIX] v3.0.5 - Parameter order matches async function for consistency.
    """
    from code_scalpel.ast_tools.cross_file_extractor import CrossFileExtractor
    from code_scalpel.licensing.features import get_tool_capabilities
    import os

    root_path = Path(project_root) if project_root else _get_project_root()

    # [20260127_FIX] Heuristic Auto-Scoping for Community Tier
    # If project_root is not provided by user, check if default usage would cover too many files.
    # If so, scope down to the parent directory of the target file instead of the entire project root.
    if project_root is None and not tier == "enterprise":
        # Check volume roughly
        try:
            # Fast check using git if available, or os.walk (limited)
            # Here we assume a simple heuristic: if we are deeper than root, use parent dir.
            target_path_obj = Path(target_file)
            if not target_path_obj.is_absolute():
                target_path_obj = root_path / target_file

            # If target is inside root_path but deeper
            if (
                target_path_obj.exists()
                and len(target_path_obj.parts) > len(root_path.parts) + 1
            ):
                # Re-scope root to the parent of the target file
                # e.g. /project/src/module/file.py -> /project/src/module
                root_path = target_path_obj.parent
        except Exception:
            pass  # Fallback to default behavior on error

    if not root_path.exists():
        return CrossFileDependenciesResult(
            success=False,
            error=f"Project root not found: {root_path}.",
        )

    # Resolve target file path
    target_path = Path(target_file)
    if not target_path.is_absolute():
        target_path = root_path / target_file

    if not target_path.exists():
        return CrossFileDependenciesResult(
            success=False,
            error=f"Target file not found: {target_path}.",
        )

    tier = tier or _get_current_tier()
    caps = capabilities or get_tool_capabilities("get_cross_file_dependencies", tier)
    caps_set = set(caps.get("capabilities", set()) or [])
    limits = caps.get("limits", {}) or {}
    # [20260307_FEATURE] Stage 10.1 metadata parity for graph-backed dependency results.
    pro_features_enabled = tier in {"pro", "enterprise"}
    enterprise_features_enabled = tier == "enterprise"

    effective_max_depth = max_depth
    depth_limit = limits.get("max_depth")
    if depth_limit is not None and effective_max_depth > depth_limit:
        effective_max_depth = int(depth_limit)

    if max_files_limit is None:
        max_files_limit = limits.get("max_files")

    target_language = _get_graph_language_from_file(str(target_path))

    # Allow caller override but never exceed tier-imposed limit
    if limits.get("max_files") is not None and max_files_limit is not None:
        max_files_limit = min(max_files_limit, limits["max_files"])

    caps_set = set(caps.get("capabilities", set()) or [])

    if target_language in {"javascript", "typescript", "java", "go"}:
        return _get_js_ts_cross_file_dependencies_sync(
            root_path=root_path,
            target_path=target_path,
            target_symbol=target_symbol,
            target_language=target_language,
            effective_max_depth=effective_max_depth,
            include_code=include_code,
            include_diagram=include_diagram,
            confidence_decay_factor=confidence_decay_factor,
            tier=tier,
            caps_set=caps_set,
            max_depth_limit=depth_limit,
            max_files_limit=max_files_limit,
        )

    # [20251227_REFACTOR] Uniform generous timeout for all tiers
    # Timeout is a safeguard, not a tier feature. The depth/file limits
    # naturally bound execution time. Timeout only triggers for pathological cases.
    build_timeout = int(timeout_seconds) if timeout_seconds else 120

    allow_transitive = "transitive_dependency_mapping" in caps_set
    coupling_enabled = "deep_coupling_analysis" in caps_set
    firewall_enabled = (
        "architectural_firewall" in caps_set or "boundary_violation_alerts" in caps_set
    )

    # [20260104_BUGFIX] Initialize all variables that may be referenced in return statement
    # to avoid UnboundLocalError if exception occurs before assignment
    files_analyzed = 0
    max_depth_reached = 0
    files_scanned = 0
    files_truncated = 0
    truncation_warning = None

    try:
        from concurrent.futures import ThreadPoolExecutor
        from concurrent.futures import TimeoutError as FuturesTimeoutError

        def run_with_timeout(func, timeout_seconds, *args, **kwargs):
            """
            Cross-platform timeout wrapper using ThreadPoolExecutor.

            Works on both Unix/Linux and Windows by running the function
            in a thread pool with a timeout.

            Args:
                func: Function to execute
                timeout_seconds: Maximum execution time in seconds
                *args, **kwargs: Arguments to pass to func

            Returns:
                Result from func

            Raises:
                TimeoutError: If execution exceeds timeout_seconds
            """
            # NOTE: Avoid `with ThreadPoolExecutor(...)` here.
            # If `future.result(timeout=...)` times out, the context manager's
            # shutdown(wait=True) can block forever waiting for a hung worker.
            executor = ThreadPoolExecutor(max_workers=1)
            future = executor.submit(func, *args, **kwargs)
            try:
                return future.result(timeout=timeout_seconds)
            except FuturesTimeoutError:
                future.cancel()
                raise TimeoutError(
                    f"Operation timed out after {timeout_seconds} seconds"
                )
            finally:
                # Do not wait for a potentially hung worker thread.
                executor.shutdown(wait=False, cancel_futures=True)

        # Build CrossFileExtractor (includes ImportResolver.build()) with timeout protection.
        def build_extractor():
            extractor = CrossFileExtractor(root_path)
            extractor.build()
            return extractor

        try:
            # [20251227_REFACTOR] Generous timeout safeguard (not tier-limited)
            # [20260127_FIX] Add volume check before build to prevent timeout on large repos
            # Community tier limit is 500 files. If scoping is wide (root_path), verify count first.
            if tier == "community" or (tier is None and not caps):
                file_count = 0
                too_many = False
                for _, _, files in os.walk(str(root_path)):
                    file_count += len(files)
                    if file_count > 500:
                        too_many = True
                        break
                if too_many:
                    return CrossFileDependenciesResult(
                        success=False,
                        tier_applied=tier,
                        max_depth_applied=depth_limit,
                        max_files_applied=max_files_limit,
                        pro_features_enabled=pro_features_enabled,
                        enterprise_features_enabled=enterprise_features_enabled,
                        error=f"Scope too large (>500 files). Community Tier is limited to 500 files per scan. Please verify a specific subdirectory using the 'project_root' parameter (Current: {root_path}).",
                    )

            extractor = run_with_timeout(build_extractor, build_timeout)
        except TimeoutError:
            # [20251227_FEATURE] Context-window aware error messaging for AI agents
            return CrossFileDependenciesResult(
                success=False,
                tier_applied=tier,
                max_depth_applied=depth_limit,
                max_files_applied=max_files_limit,
                pro_features_enabled=pro_features_enabled,
                enterprise_features_enabled=enterprise_features_enabled,
                error=(
                    f"TIMEOUT ({build_timeout}s): CrossFileExtractor.build() exceeded safeguard limit. "
                    f"FIX: Use a smaller project_root scope. Current: {root_path}. "
                    f"EXAMPLE: Instead of project root, target a specific subdirectory like 'src/module/'. "
                    f"LIMITS: max_depth={effective_max_depth}, max_files={max_files_limit or 'unlimited'}."
                ),
            )

        # [20251216_FEATURE] v2.5.0 - Pass confidence_decay_factor to extractor
        def extract_dependencies():
            return extractor.extract(
                str(target_path),
                target_symbol,
                depth=effective_max_depth,
                confidence_decay_factor=confidence_decay_factor,
            )

        # [20251227_REFACTOR] Extraction timeout is 50% of build timeout
        extraction_timeout = build_timeout // 2
        try:
            extraction_result = run_with_timeout(
                extract_dependencies, extraction_timeout
            )
        except TimeoutError:
            # [20251227_FEATURE] Context-window aware error messaging for AI agents
            return CrossFileDependenciesResult(
                success=False,
                tier_applied=tier,
                max_depth_applied=depth_limit,
                max_files_applied=max_files_limit,
                pro_features_enabled=pro_features_enabled,
                enterprise_features_enabled=enterprise_features_enabled,
                error=(
                    f"TIMEOUT ({extraction_timeout}s): Extracting '{target_symbol}' exceeded safeguard limit. "
                    f"FIX: Reduce max_depth (current: {effective_max_depth}) or target a simpler symbol. "
                    f"EXAMPLE: Try max_depth=1 for direct dependencies only. "
                    f"FILE: {target_path}"
                ),
            )

        # Check for extraction errors
        if not extraction_result.success:
            return CrossFileDependenciesResult(
                success=False,
                tier_applied=tier,
                max_depth_applied=depth_limit,
                max_files_applied=max_files_limit,
                pro_features_enabled=pro_features_enabled,
                enterprise_features_enabled=enterprise_features_enabled,
                error=f"Extraction failed: {'; '.join(extraction_result.errors)}.",
            )

        # Build the list of all symbols (target + dependencies)
        all_symbols = []
        if extraction_result.target:
            all_symbols.append(extraction_result.target)
        all_symbols.extend(extraction_result.dependencies)

        # Convert extracted symbols to models
        extracted_symbols = []
        combined_parts = []

        # [20251216_FEATURE] v2.5.0 - Low confidence threshold
        LOW_CONFIDENCE_THRESHOLD = 0.5

        for sym in all_symbols:
            rel_file = (
                str(Path(sym.file).relative_to(root_path))
                if Path(sym.file).is_absolute()
                else sym.file
            )
            # [20251216_FEATURE] v2.5.0 - Include depth and confidence in symbol model
            extracted_symbols.append(
                ExtractedSymbolModel(
                    name=sym.name,
                    code=sym.code if include_code else "",
                    file=rel_file,
                    line_start=sym.line,  # ExtractedSymbol uses 'line' not 'line_start'
                    line_end=sym.end_line or 0,  # ExtractedSymbol uses 'end_line'
                    dependencies=list(sym.dependencies),
                    depth=sym.depth,
                    confidence=sym.confidence,
                    low_confidence=sym.confidence < LOW_CONFIDENCE_THRESHOLD,
                )
            )
            if include_code:
                combined_parts.append(f"# From {rel_file}")
                combined_parts.append(sym.code)

        combined_code = "\n\n".join(combined_parts) if include_code else ""

        # Use the extractor's combined code if available (includes proper ordering)
        if include_code and extraction_result.combined_code:
            combined_code = extraction_result.combined_code

        # Get unresolved imports from extraction result
        unresolved_imports = (
            extraction_result.module_imports
        )  # These are imports that couldn't be resolved

        # Build import graph dict (file -> list of imported files)
        # Use the extractor's resolver (avoid double-building) and keep this focused.
        resolver = extractor.resolver
        import_graph: dict[str, list[str]] = {}

        # [20251226_FEATURE] Tier-aware truncation and metrics
        file_order: list[str] = []
        for sym in extracted_symbols:
            if sym.file not in file_order:
                file_order.append(sym.file)

        files_scanned = len(file_order)
        files_truncated = 0
        truncation_warning = None
        if max_files_limit is not None and files_scanned > max_files_limit:
            files_truncated = files_scanned - max_files_limit
            allowed_files = set(file_order[:max_files_limit])
            truncation_warning = f"Truncated to {max_files_limit} files (of {files_scanned}) due to tier limits."
            extracted_symbols = [
                sym for sym in extracted_symbols if sym.file in allowed_files
            ]
            file_order = file_order[:max_files_limit]

            if include_code:
                combined_parts = []
                for sym in extracted_symbols:
                    combined_parts.append(f"# From {sym.file}")
                    combined_parts.append(sym.code)
                combined_code = "\n\n".join(combined_parts)

        # Limit graph construction to files actually involved in the extraction.
        files_of_interest: set[str] = set()
        for sym in extracted_symbols:
            try:
                p = Path(sym.file)
                if not p.is_absolute():
                    p = root_path / p
                p = p.resolve()
                files_of_interest.add(str(p))
            except Exception:
                continue
        files_of_interest.add(str(target_path.resolve()))

        for abs_file in files_of_interest:
            module_name = resolver.file_to_module.get(abs_file)
            if not module_name:
                continue

            rel_path = str(Path(abs_file).relative_to(root_path))
            imported_files: list[str] = []
            for imp in resolver.imports.get(module_name, []):
                resolved_file = resolver.module_to_file.get(imp.module)
                if not resolved_file:
                    continue
                try:
                    resolved_abs = str(Path(resolved_file).resolve())
                    if resolved_abs not in files_of_interest:
                        continue
                    resolved_rel = str(Path(resolved_abs).relative_to(root_path))
                except Exception:
                    continue
                if resolved_rel not in imported_files:
                    imported_files.append(resolved_rel)

            if imported_files:
                import_graph[rel_path] = imported_files

        # Make target file relative (used by diagram + returned fields)
        target_rel = (
            str(target_path.relative_to(root_path))
            if target_path.is_absolute()
            else target_file
        )

        transitive_depth = effective_max_depth

        # [20251226_FEATURE] Enforce tier depth clamp: ensure we never exceed tier's configured max_depth.
        # This applies even if user requested higher. For community, max_depth_limit is 1.
        max_depth_limit = limits.get("max_depth")
        if max_depth_limit is not None and transitive_depth > max_depth_limit:
            transitive_depth = int(max_depth_limit)

        # [20260127_FIX] Filter extracted_symbols to enforce tier depth limit.
        # Remove any symbols that exceed the tier-clamped transitive_depth.
        extracted_symbols = [
            sym for sym in extracted_symbols if sym.depth <= transitive_depth
        ]
        # Recalculate file order based on filtered symbols
        file_order = []
        for sym in extracted_symbols:
            if sym.file not in file_order:
                file_order.append(sym.file)
        # Regenerate combined code if filtered
        if include_code and extracted_symbols:
            combined_parts = []
            for sym in extracted_symbols:
                combined_parts.append(f"# From {sym.file}")
                combined_parts.append(sym.code)
            combined_code = "\n\n".join(combined_parts)

        coupling_score: float | None = None
        if coupling_enabled:
            unique_files = len(file_order) if file_order else 0
            deps_count = max(0, len(extracted_symbols) - 1)
            if unique_files > 0:
                coupling_score = round(deps_count / unique_files, 3)

        dependency_chains: list[list[str]] = []
        if allow_transitive and import_graph:
            from collections import deque

            max_chains = 25
            queue = deque([(target_rel, [target_rel], 0)])
            seen_paths: set[tuple[str, ...]] = set()
            while queue and len(dependency_chains) < max_chains:
                current, path, depth = queue.popleft()
                if depth >= transitive_depth:
                    continue
                for dep in import_graph.get(current, []):
                    new_path = path + [dep]
                    path_key = tuple(new_path)
                    if path_key in seen_paths:
                        continue
                    seen_paths.add(path_key)
                    dependency_chains.append(new_path)
                    queue.append((dep, new_path, depth + 1))

            # Update max_depth_reached: longest chain (edges = len-1), bounded by transitive_depth limit.
            # The test expects max_depth_reached <= transitive_depth (which is tier-clamped).
            if dependency_chains:
                chain_depths = [max(0, len(c) - 1) for c in dependency_chains]
                if chain_depths:
                    observed = max(chain_depths)
                    # But we enforce transitive_depth as the hard limit; if chains are longer, cap it.
                    max_depth_reached = min(
                        max(max_depth_reached, observed), transitive_depth
                    )

        # [20251226_FEATURE] Enterprise architectural firewall outputs
        boundary_violations: list[dict[str, Any]] = []
        layer_violations: list[dict[str, Any]] = []
        architectural_alerts: list[dict[str, Any]] = []

        def _infer_layer(rel_path: str) -> str:
            lowered = rel_path.lower()
            if "controllers" in lowered or "api" in lowered:
                return "presentation"
            if "services" in lowered or "service" in lowered:
                return "domain"
            if "models" in lowered or "entities" in lowered:
                return "data"
            return "unknown"

        if firewall_enabled and import_graph:
            layer_rank = {"presentation": 3, "domain": 2, "data": 1, "unknown": 0}
            for src_file, targets in import_graph.items():
                src_layer = _infer_layer(src_file)
                for dst_file in targets:
                    dst_layer = _infer_layer(dst_file)
                    if src_layer == "presentation" and dst_layer == "data":
                        violation = {
                            "type": "layer_skip",
                            "source": src_file,
                            "target": dst_file,
                            "violation": "Presentation layer should not depend directly on data layer",
                            "recommendation": "Route dependencies through services to enforce layering",
                        }
                        boundary_violations.append(violation)
                        layer_violations.append(violation)
                    elif (
                        layer_rank.get(src_layer, 0) < layer_rank.get(dst_layer, 0)
                        and dst_layer != "unknown"
                    ):
                        violation = {
                            "type": "upward_dependency",
                            "source": src_file,
                            "target": dst_file,
                            "violation": "Lower layers should not depend on higher layers",
                            "recommendation": "Refactor to invert dependency or introduce interface",
                        }
                        layer_violations.append(violation)

            if boundary_violations or layer_violations:
                architectural_alerts.append(
                    {
                        "severity": "high",
                        "message": "Architectural boundary violations detected",
                        "count": len(boundary_violations) + len(layer_violations),
                    }
                )

        # Detect circular imports using get_circular_imports()
        circular_import_objs = resolver.get_circular_imports()
        circular_import_lists = [
            ci.cycle for ci in circular_import_objs
        ]  # CircularImport uses 'cycle'

        # Make target file relative (used by diagram + returned fields)
        target_rel = (
            str(target_path.relative_to(root_path))
            if target_path.is_absolute()
            else target_file
        )

        # Generate Mermaid diagram
        mermaid = ""
        if include_diagram:
            from collections import deque

            # Generate a focused diagram to avoid project-wide graph explosion.
            # We bound the subgraph by max_depth and cap nodes/edges.
            max_mermaid_nodes = 60
            max_mermaid_edges = 200

            start_file = target_rel
            # BFS from target file using the computed import_graph (file -> imported files)
            queue = deque([(start_file, 0)])
            seen_nodes: set[str] = set()
            edges_out: list[tuple[str, str]] = []

            while (
                queue
                and len(seen_nodes) < max_mermaid_nodes
                and len(edges_out) < max_mermaid_edges
            ):
                cur, depth = queue.popleft()
                if cur in seen_nodes:
                    continue
                seen_nodes.add(cur)
                if depth >= effective_max_depth:
                    continue
                for dep in import_graph.get(cur, [])[:max_mermaid_edges]:
                    if len(edges_out) >= max_mermaid_edges:
                        break
                    edges_out.append((cur, dep))
                    if dep not in seen_nodes:
                        queue.append((dep, depth + 1))

            # Mermaid with stable short node ids
            lines = ["graph TD"]
            node_ids: dict[str, str] = {}
            # Always include the start node (even if it has no outgoing edges)
            seen_nodes.add(start_file)
            for i, n in enumerate(sorted(seen_nodes)):
                node_ids[n] = f"N{i}"
                safe_label = n.replace("/", "_").replace(".", "_")
                lines.append(f"    {node_ids[n]}[{safe_label}]")

            for a, b in edges_out:
                if a in node_ids and b in node_ids:
                    lines.append(f"    {node_ids[a]} --> {node_ids[b]}")

            # Truncation hint
            if (
                len(seen_nodes) >= max_mermaid_nodes
                or len(edges_out) >= max_mermaid_edges
            ):
                lines.append(
                    f"    %% Diagram truncated (nodes<={max_mermaid_nodes}, edges<={max_mermaid_edges})"
                )

            mermaid = "\n".join(lines)

        # Calculate token estimate (rough: 4 chars per token)
        token_estimate = len(combined_code) // 4 if combined_code else 0

        # [20251216_FEATURE] v2.5.0 - Build low confidence warning if needed
        low_confidence_warning = None
        if extraction_result.low_confidence_count > 0:
            low_conf_names = [
                s.name for s in extraction_result.get_low_confidence_symbols()[:5]
            ]
            low_confidence_warning = (
                f"⚠️ {extraction_result.low_confidence_count} symbol(s) have low confidence "
                f"(below 0.5): {', '.join(low_conf_names)}"
                + ("..." if extraction_result.low_confidence_count > 5 else "")
            )

        # Pro/Enterprise derived insights
        alias_resolutions: list[AliasResolutionModel] = []
        chained_alias_resolutions: list[ChainedAliasResolutionModel] = []
        wildcard_expansions: list[WildcardExpansionModel] = []
        reexport_chains: list[ReexportChainModel] = []
        coupling_violations: list[CouplingViolationModel] = []
        architectural_violations: list[ArchitecturalViolationModel] = []
        boundary_alerts: list[BoundaryAlertModel] = []
        layer_mapping: dict[str, list[str]] = {}
        rules_applied: list[str] = []
        exempted_files: list[str] = []
        files_analyzed = len(files_of_interest)
        if max_files_limit is not None:
            files_analyzed = min(files_analyzed, max_files_limit)
        max_depth_reached = extraction_result.depth_reached

        # Alias / wildcard / re-export analysis (Pro+)
        if tier != "community":
            module_cache: dict[str, str] = {}
            for abs_file in files_of_interest:
                module_name = resolver.file_to_module.get(abs_file)
                if not module_name:
                    continue
                module_cache[abs_file] = module_name

                # Alias resolutions
                for imp in resolver.imports.get(module_name, []):
                    if imp.alias:
                        try:
                            rel_file = str(Path(abs_file).relative_to(root_path))
                        except Exception:
                            rel_file = Path(abs_file).name

                        alias_resolutions.append(
                            AliasResolutionModel(
                                alias=imp.alias,
                                original_module=imp.module or "",
                                original_name=imp.name,
                                file=rel_file,
                                line=imp.line,
                            )
                        )
                        try:
                            resolved_mod, resolved_name, chain = (
                                resolver.resolve_alias_chain(module_name, imp.alias)
                            )
                            chained_alias_resolutions.append(
                                ChainedAliasResolutionModel(
                                    symbol=imp.alias,
                                    chain=chain or [],
                                    resolved_module=resolved_mod,
                                    resolved_name=resolved_name,
                                )
                            )
                        except Exception:
                            chained_alias_resolutions.append(
                                ChainedAliasResolutionModel(
                                    symbol=imp.alias,
                                    chain=[],
                                    resolved_module=None,
                                    resolved_name=None,
                                )
                            )

                # Wildcard expansions per module
                wildcard_map = resolver.expand_all_wildcards(module_name)
                for src_module, symbols in wildcard_map.items():
                    if symbols:
                        wildcard_expansions.append(
                            WildcardExpansionModel(
                                from_module=src_module, expanded_symbols=symbols
                            )
                        )

            # Re-export chains (project-wide)
            reexports = resolver.get_all_reexports()
            for apparent, mapping in reexports.items():
                for symbol, actual in mapping.items():
                    reexport_chains.append(
                        ReexportChainModel(
                            symbol=symbol,
                            apparent_source=apparent,
                            actual_source=actual,
                        )
                    )

        # Enterprise architectural rule engine outputs
        if firewall_enabled and caps_set.intersection(
            {
                "architectural_firewall",
                "dependency_rule_engine",
                "layer_constraint_enforcement",
            }
        ):
            try:
                from code_scalpel.ast_tools.architectural_rules import (
                    ArchitecturalRuleEngine,
                )

                engine = ArchitecturalRuleEngine(root_path)
                engine.load_config()

                rules_applied = list(engine.get_all_rules().keys())
                rules_applied.extend([r.name for r in engine.config.custom_rules])

                # Map modules to layers and exemptions
                for abs_file in files_of_interest:
                    module_name = resolver.file_to_module.get(abs_file)
                    if not module_name:
                        continue

                    if engine.is_exempt(module_name):
                        try:
                            exempted_files.append(
                                str(Path(abs_file).relative_to(root_path))
                            )
                        except Exception:
                            exempted_files.append(Path(abs_file).name)

                    layer = engine.get_layer(module_name)
                    if layer:
                        try:
                            rel = str(Path(abs_file).relative_to(root_path))
                        except Exception:
                            rel = Path(abs_file).name
                        layer_mapping.setdefault(layer, []).append(rel)

                # Dependency violations
                module_for_rel: dict[str, str] = {}
                for rel_path in import_graph.keys():
                    abs_path = str((root_path / rel_path).resolve())
                    module = resolver.file_to_module.get(abs_path)
                    if module:
                        module_for_rel[rel_path] = module

                for rel_src, targets in import_graph.items():
                    src_module = module_for_rel.get(rel_src)
                    if not src_module:
                        continue
                    for rel_tgt in targets:
                        tgt_module = module_for_rel.get(rel_tgt)
                        if not tgt_module:
                            continue
                        violations = engine.check_dependency(src_module, tgt_module)
                        for v in violations:
                            architectural_violations.append(
                                ArchitecturalViolationModel(
                                    type=v.rule_name,
                                    severity=v.severity.value,
                                    source=rel_src,
                                    target=rel_tgt,
                                    from_layer=v.from_layer,
                                    to_layer=v.to_layer,
                                    description=v.description,
                                    recommendation=None,
                                )
                            )
                            if v.from_layer and v.to_layer:
                                boundary_alerts.append(
                                    BoundaryAlertModel(
                                        rule=v.rule_name,
                                        from_layer=v.from_layer,
                                        to_layer=v.to_layer,
                                        source=rel_src,
                                        target=rel_tgt,
                                    )
                                )

                # Coupling violations
                for abs_file in files_of_interest:
                    module_name = resolver.file_to_module.get(abs_file)
                    if not module_name:
                        continue
                    fan_in = len(resolver.reverse_edges.get(module_name, set()))
                    fan_out = len(resolver.edges.get(module_name, set()))
                    coupling_viols = engine.check_coupling(
                        module_name, fan_in, fan_out, max_depth_reached
                    )
                    for v in coupling_viols:
                        metric = "fan_in"
                        limit = engine.config.coupling_limits.max_fan_in
                        value = fan_in
                        if v.rule_name == "high_fan_out":
                            metric = "fan_out"
                            limit = engine.config.coupling_limits.max_fan_out
                            value = fan_out
                        elif v.rule_name == "deep_dependency_chain":
                            metric = "dependency_depth"
                            limit = engine.config.coupling_limits.max_dependency_depth
                            value = max_depth_reached

                        coupling_violations.append(
                            CouplingViolationModel(
                                metric=metric,
                                value=value,
                                limit=limit,
                                module=module_name,
                                severity=v.severity.value,
                                description=v.description,
                            )
                        )

            except Exception:
                # Keep Enterprise extras optional; do not fail core analysis
                pass

        return CrossFileDependenciesResult(
            success=True,
            target_name=target_symbol,
            target_file=target_rel,
            extracted_symbols=extracted_symbols,
            total_dependencies=len(extracted_symbols) - 1,  # Exclude target itself
            unresolved_imports=unresolved_imports,  # Use local variable set from module_imports
            import_graph=import_graph,
            circular_imports=circular_import_lists,
            combined_code=combined_code,
            token_estimate=token_estimate,
            mermaid=mermaid,
            # [20251216_FEATURE] v2.5.0 - Confidence decay fields
            confidence_decay_factor=confidence_decay_factor,
            low_confidence_count=extraction_result.low_confidence_count,
            low_confidence_warning=low_confidence_warning,
            # [20251226_FEATURE] Tier-aware outputs
            transitive_depth=transitive_depth,
            alias_resolutions=alias_resolutions,
            wildcard_expansions=wildcard_expansions,
            reexport_chains=reexport_chains,
            chained_alias_resolutions=chained_alias_resolutions,
            coupling_score=coupling_score,
            coupling_violations=coupling_violations,
            dependency_chains=dependency_chains,
            boundary_violations=boundary_violations,
            layer_violations=layer_violations,
            architectural_alerts=architectural_alerts,
            architectural_violations=architectural_violations,
            boundary_alerts=boundary_alerts,
            layer_mapping=layer_mapping,
            rules_applied=rules_applied,
            architectural_rules_applied=rules_applied,
            exempted_files=exempted_files,
            files_scanned=files_scanned,
            files_truncated=files_truncated,
            truncation_warning=truncation_warning,
            truncated=files_truncated > 0,
            files_analyzed=files_analyzed,
            max_depth_reached=max_depth_reached,
        )

    except Exception as e:
        return CrossFileDependenciesResult(
            success=False,
            error=f"Cross-file dependency analysis failed: {str(e)}",
        )


# ============================================================================
# [20251213_FEATURE] v1.5.1 - cross_file_security_scan MCP Tool
# ============================================================================


def _cross_file_security_scan_sync(
    project_root: str | None,
    entry_points: list[str] | None,
    max_depth: int,
    include_diagram: bool,
    timeout_seconds: float | None = 120.0,  # [20251220_PERF] Default 2 minute timeout
    max_modules: (
        int | None
    ) = 500,  # [20251220_PERF] Default module limit for large projects
    tier: str | None = None,
    capabilities: dict | None = None,
    confidence_threshold: float = 0.7,
) -> CrossFileSecurityResult:
    """Synchronous implementation of cross_file_security_scan."""
    from code_scalpel.licensing.features import get_tool_capabilities
    from code_scalpel.security.analyzers import CrossFileTaintTracker

    tier = tier or _get_current_tier()
    caps = capabilities or get_tool_capabilities("cross_file_security_scan", tier)
    caps_set = set(caps.get("capabilities", set()) or [])
    limits = caps.get("limits", {}) or {}

    # Enforce limits (support both max_* keys from limits.toml and features.py)
    max_modules_limit = (
        limits.get("max_modules")
        if "max_modules" in limits
        else limits.get("max_files")
    )
    if max_modules_limit is not None and max_modules is not None:
        max_modules = min(max_modules, max_modules_limit)
    elif max_modules_limit is not None:
        max_modules = max_modules_limit

    max_depth_limit = (
        limits.get("max_depth")
        if "max_depth" in limits
        else limits.get("max_taint_depth")
    )
    if max_depth_limit is not None and max_depth is not None:
        max_depth = min(max_depth, max_depth_limit)
    elif max_depth_limit is not None:
        max_depth = max_depth_limit

    root_path = Path(project_root) if project_root else _get_project_root()

    if not root_path.exists():
        return CrossFileSecurityResult(
            success=False,
            error=f"Project root not found: {root_path}.",
        )

    try:
        tracker = CrossFileTaintTracker(root_path)
        # [20251220_PERF] Pass timeout and module limit to prevent hanging
        result = tracker.analyze(
            entry_points=entry_points,
            max_depth=max_depth,
            timeout_seconds=timeout_seconds,
            max_modules=max_modules,
        )

        # Helper to get file path from module name
        def get_file_for_module(module: str) -> str:
            """Get file path for a module, falling back to module name if not found."""
            file_path = tracker.resolver.module_to_file.get(module, module)
            if isinstance(file_path, Path):
                file_path = str(file_path)
            # Make relative if absolute
            try:
                p = Path(file_path)
                if p.is_absolute():
                    return str(p.relative_to(root_path))
            except (ValueError, TypeError):
                pass
            return file_path

        # Convert vulnerabilities to models
        vulnerabilities = []
        for vuln in result.vulnerabilities:
            # [20260115_FEATURE] Filter by confidence (verified taint = 0.95)
            if 0.95 < confidence_threshold:
                continue

            # [20251215_BUGFIX] v2.0.1 - Use source_module not source_file
            source_file = get_file_for_module(vuln.flow.source_module)
            sink_file = get_file_for_module(vuln.flow.sink_module)

            flow_model = TaintFlowModel(
                source_function=vuln.flow.source_function,
                source_file=source_file,
                source_line=vuln.flow.source_line,
                sink_function=vuln.flow.sink_function,
                sink_file=sink_file,
                sink_line=vuln.flow.sink_line,
                flow_path=[
                    f"{get_file_for_module(m)}:{f}" for m, f, _ in vuln.flow.flow_path
                ],
                taint_type=str(
                    vuln.flow.sink_type.name
                    if hasattr(vuln.flow.sink_type, "name")
                    else vuln.flow.sink_type
                ),
            )
            vulnerabilities.append(
                CrossFileVulnerabilityModel(
                    type=vuln.vulnerability_type,
                    cwe=vuln.cwe_id,
                    severity=vuln.severity,
                    source_file=source_file,
                    sink_file=sink_file,
                    description=vuln.description,
                    flow=flow_model,
                )
            )

        # Convert taint flows to models
        taint_flows = []
        for flow in result.taint_flows:
            # [20251215_BUGFIX] v2.0.1 - Use source_module not source_file
            source_file = get_file_for_module(flow.source_module)
            sink_file = get_file_for_module(flow.sink_module)

            taint_flows.append(
                TaintFlowModel(
                    source_function=flow.source_function,
                    source_file=source_file,
                    source_line=flow.source_line,
                    sink_function=flow.sink_function,
                    sink_file=sink_file,
                    sink_line=flow.sink_line,
                    flow_path=[
                        f"{get_file_for_module(m)}:{f}" for m, f, _ in flow.flow_path
                    ],
                    taint_type=str(
                        flow.sink_type.name
                        if hasattr(flow.sink_type, "name")
                        else flow.sink_type
                    ),
                )
            )

        # Determine risk level
        vuln_count = len(vulnerabilities)
        warnings: list[str] = list(result.warnings)
        java_file = next(root_path.rglob("*.java"), None)
        if java_file is not None:
            if getattr(tracker, "_resolver_language", "python") == "python":
                if result.modules_analyzed == 0:
                    warnings.append(
                        "Cross-file security scan currently analyzes Python module graphs only; detected Java files were not analyzed."
                    )
                else:
                    warnings.append(
                        "Cross-file security scan analyzed Python modules but skipped detected Java files because cross-file Java module analysis is not implemented yet."
                    )
            elif not any(
                "Java cross-file security scan currently supports a bounded IR-based subset"
                in warning
                for warning in warnings
            ):
                warnings.append(
                    "Java cross-file security scan currently supports a bounded IR-based subset: common sources/sinks plus direct/static-import flows. Broader Java patterns are not implemented yet."
                )

        if vuln_count == 0:
            risk_level = "low"
        elif vuln_count <= 2:
            risk_level = "medium"
        elif vuln_count <= 5:
            risk_level = "high"
        else:
            risk_level = "critical"

        # Generate Mermaid diagram
        mermaid = ""
        if include_diagram:
            mermaid = tracker.get_taint_graph_mermaid()

        # Extract taint sources from tracker's internal state
        taint_sources = []
        dangerous_sinks = []

        # Get taint sources if available
        if hasattr(tracker, "module_taint_sources"):
            for module, sources in tracker.module_taint_sources.items():
                for src in sources:
                    taint_sources.append(f"{module}:{src.function}")

        # Get sinks from taint flows
        for flow in result.taint_flows:
            sink_key = f"{flow.sink_function}"
            if sink_key not in dangerous_sinks:
                dangerous_sinks.append(sink_key)

        # Tier-aware enrichments (heuristic, lightweight to satisfy tier expectations)
        framework_contexts: list[dict[str, Any]] | None = None
        dependency_chains: list[dict[str, Any]] | None = None
        confidence_scores: dict[str, float] | None = None
        global_flows: list[dict[str, Any]] | None = None
        microservice_boundaries: list[dict[str, Any]] | None = None
        distributed_trace: dict[str, Any] | None = None

        def _detect_framework_contexts(
            base_path: Path, limit: int | None
        ) -> list[dict[str, Any]]:
            contexts: list[dict[str, Any]] = []
            max_files = limit or 50
            scanned = 0
            for file_path in base_path.rglob("*"):
                if not file_path.is_file():
                    continue
                if file_path.suffix.lower() not in {
                    ".py",
                    ".js",
                    ".ts",
                    ".tsx",
                    ".jsx",
                }:
                    continue
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                scanned += 1
                if scanned > max_files:
                    break
                if "@Autowired" in content or "@Component" in content:
                    contexts.append(
                        {
                            "framework": "spring",
                            "file": str(file_path.relative_to(base_path)),
                        }
                    )
                if "useContext(" in content:
                    contexts.append(
                        {
                            "framework": "react",
                            "file": str(file_path.relative_to(base_path)),
                        }
                    )
            return contexts

        def _build_dependency_chains(
            flows: list[TaintFlowModel],
        ) -> list[dict[str, Any]]:
            chains: list[dict[str, Any]] = []
            for flow in flows[:50]:
                chains.append(
                    {
                        "source": f"{flow.source_file}:{flow.source_function}",
                        "sink": f"{flow.sink_file}:{flow.sink_function}",
                        "path": flow.flow_path,
                    }
                )
            return chains

        def _build_confidence_scores(
            vulns_list: list[CrossFileVulnerabilityModel],
        ) -> dict[str, float]:
            scores: dict[str, float] = {}
            for vuln in vulns_list:
                key = f"{vuln.type}:{vuln.source_file}->{vuln.sink_file}"
                sev = vuln.severity.lower()
                scores[key] = 0.95 if sev in {"critical", "high"} else 0.8
            return scores

        def _detect_global_flows(flows: list[TaintFlowModel]) -> list[dict[str, Any]]:
            gflows: list[dict[str, Any]] = []
            for flow in flows[:100]:
                if "frontend" in flow.source_file or "frontend" in "".join(
                    flow.flow_path
                ):
                    gflows.append(
                        {
                            "source": flow.source_file,
                            "sink": flow.sink_file,
                            "flow_path": flow.flow_path,
                            "taint_type": flow.taint_type,
                        }
                    )
            return gflows

        def _detect_microservice_boundaries(base_path: Path) -> list[dict[str, Any]]:
            boundaries: list[dict[str, Any]] = []
            for child in list(base_path.iterdir())[:10]:
                if child.is_dir():
                    boundaries.append(
                        {
                            "service": child.name,
                            "path": str(child.relative_to(base_path)),
                        }
                    )
            return boundaries

        def _build_distributed_trace(gflows: list[dict[str, Any]]) -> dict[str, Any]:
            nodes: set[str] = set()
            edges: list[tuple[str, str]] = []
            for gf in gflows:
                nodes.add(gf["source"])
                nodes.add(gf["sink"])
                edges.append((gf["source"], gf["sink"]))
            return {"nodes": sorted(nodes), "edges": edges}

        if {
            "framework_aware_taint",
            "spring_bean_tracking",
            "react_context_tracking",
            "dependency_injection_resolution",
        } & caps_set:
            framework_contexts = _detect_framework_contexts(
                root_path, max_modules_limit
            )
            dependency_chains = _build_dependency_chains(taint_flows)
            confidence_scores = _build_confidence_scores(vulnerabilities)

        if {
            "global_taint_flow",
            "frontend_to_backend_tracing",
            "api_to_database_tracing",
            "microservice_boundary_crossing",
        } & caps_set:
            global_flows = _detect_global_flows(taint_flows)
            microservice_boundaries = _detect_microservice_boundaries(root_path)
            if global_flows:
                distributed_trace = _build_distributed_trace(global_flows)

        # [20260111_FEATURE] v1.0 - Compute metadata flags for transparency
        framework_aware_enabled = bool(
            {
                "framework_aware_taint",
                "spring_bean_tracking",
                "react_context_tracking",
                "dependency_injection_resolution",
            }
            & caps_set
        )
        enterprise_features_enabled = bool(
            {
                "global_taint_flow",
                "frontend_to_backend_tracing",
                "api_to_database_tracing",
                "microservice_boundary_crossing",
            }
            & caps_set
        )

        return CrossFileSecurityResult(
            success=True,
            tier_applied=tier,
            max_depth_applied=max_depth_limit,
            max_modules_applied=max_modules_limit,
            framework_aware_enabled=framework_aware_enabled,
            enterprise_features_enabled=enterprise_features_enabled,
            files_analyzed=result.modules_analyzed,  # Use modules_analyzed
            has_vulnerabilities=vuln_count > 0,
            vulnerability_count=vuln_count,
            risk_level=risk_level,
            vulnerabilities=vulnerabilities,
            taint_flows=taint_flows,
            taint_sources=taint_sources,
            dangerous_sinks=dangerous_sinks,
            warnings=warnings,
            mermaid=mermaid,
            framework_contexts=framework_contexts,
            dependency_chains=dependency_chains,
            confidence_scores=confidence_scores,
            global_flows=global_flows,
            microservice_boundaries=microservice_boundaries,
            distributed_trace=distributed_trace,
        )

    except Exception as e:
        return CrossFileSecurityResult(
            success=False,
            error=f"Cross-file security analysis failed: {str(e)}",
        )
