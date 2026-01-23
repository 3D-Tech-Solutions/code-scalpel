"""
Cross-File Code Extractor for Surgical Operations.

[20251213_FEATURE] v1.5.1 - Cross-file extraction with dependency resolution

This module enables extracting code symbols (functions, classes, methods) along with
their cross-file dependencies, providing complete context for AI-assisted editing.

Key features:
- Extract function/class with all imported dependencies
- Follow import chains to gather complete context
- Limit depth to prevent explosion
- Generate minimal extraction (only what's needed)

Example:
    >>> from code_scalpel.ast_tools.cross_file_extractor import CrossFileExtractor
    >>> extractor = CrossFileExtractor("/path/to/project")
    >>> result = extractor.extract("src/views.py", "process_request", depth=2)
    >>> print(result.code)  # Function with imported dependencies
"""

import ast
import os
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from .import_resolver import ImportInfo, ImportResolver


@dataclass
class ExtractedSymbol:
    """
    A single extracted code symbol.

    Attributes:
        name: Symbol name
        symbol_type: Type (function, class, method)
        module: Module where defined
        file: Absolute file path
        code: Extracted source code
        line: Start line in original file
        end_line: End line in original file
        dependencies: Names of symbols this depends on
        depth: Depth from original target (0 = target itself)
        confidence: Confidence score with decay applied (0.0-1.0)

    """

    name: str
    symbol_type: str
    module: str
    file: str
    code: str
    line: int
    end_line: int | None = None
    dependencies: set[str] = field(default_factory=set)
    # [20251216_FEATURE] v2.5.0 - Confidence decay for deep dependency chains
    depth: int = 0
    confidence: float = 1.0

    def __hash__(self):
        return hash((self.module, self.name))

    def __eq__(self, other):
        if not isinstance(other, ExtractedSymbol):
            return False
        return self.module == other.module and self.name == other.name


# [20251216_FEATURE] v2.5.0 - Confidence decay constants
DEFAULT_CONFIDENCE_DECAY_FACTOR = 0.9
DEFAULT_LOW_CONFIDENCE_THRESHOLD = 0.5


def calculate_confidence(depth: int, decay_factor: float = DEFAULT_CONFIDENCE_DECAY_FACTOR) -> float:
    """
    Calculate confidence score with exponential decay based on depth.

    Formula: C_effective = C_base × decay_factor^depth

    Args:
        depth: Depth from original target (0 = target itself)
        decay_factor: Decay rate per depth level (default: 0.9)

    Returns:
        Confidence score between 0.0 and 1.0
    """
    # [20251216_BUGFIX] Clamp/validate to prevent amplification or negative confidence
    if depth < 0:
        raise ValueError("depth must be >= 0")
    if decay_factor < 0:
        raise ValueError("decay_factor must be >= 0")
    # Clamp >1 to 1.0 to prevent confidence amplification attacks
    safe_decay = min(decay_factor, 1.0)

    # Compute with clamp; guard against float domain issues
    conf = 1.0 * (safe_decay**depth)
    if conf != conf or conf == float("inf") or conf < 0:  # NaN or Inf or negative
        raise ValueError("invalid confidence result")

    return round(conf, 4)


@dataclass
class ExtractionResult:
    """
    Result of a cross-file extraction operation.

    Attributes:
        success: Whether extraction succeeded
        target: The primary symbol that was requested
        dependencies: List of dependency symbols extracted
        combined_code: All extracted code combined in dependency order
        module_imports: Import statements needed
        errors: Any errors encountered
        warnings: Non-fatal warnings
        depth_reached: Maximum depth of dependency chain
        files_touched: Set of files that were read
        confidence_decay_factor: Decay factor used for confidence calculation
        low_confidence_count: Number of symbols below low confidence threshold
    """

    success: bool = True
    target: ExtractedSymbol | None = None
    dependencies: list[ExtractedSymbol] = field(default_factory=list)
    combined_code: str = ""
    module_imports: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    depth_reached: int = 0
    files_touched: set[str] = field(default_factory=set)
    # [20251216_FEATURE] v2.5.0 - Confidence decay tracking
    confidence_decay_factor: float = DEFAULT_CONFIDENCE_DECAY_FACTOR
    low_confidence_count: int = 0

    @property
    def total_symbols(self) -> int:
        """Total number of symbols extracted (target + dependencies)."""
        count = len(self.dependencies)
        if self.target:
            count += 1
        return count

    @property
    def total_lines(self) -> int:
        """Total lines of code extracted."""
        return self.combined_code.count("\n") + 1 if self.combined_code else 0

    @property
    def has_low_confidence_symbols(self) -> bool:
        """Check if any extracted symbols have low confidence."""
        return self.low_confidence_count > 0

    def get_low_confidence_symbols(self, threshold: float = DEFAULT_LOW_CONFIDENCE_THRESHOLD) -> list[ExtractedSymbol]:
        """Get all symbols below the confidence threshold."""
        low_conf = []
        if self.target and self.target.confidence < threshold:
            low_conf.append(self.target)
        for dep in self.dependencies:
            if dep.confidence < threshold:
                low_conf.append(dep)
        return low_conf


@dataclass
class DependencyNode:
    """
    Node in the dependency graph during extraction.

    Attributes:
        symbol_name: Name of the symbol
        module: Module where defined
        depth: Depth from original target
        import_info: How this symbol was imported (if applicable)
    """

    symbol_name: str
    module: str
    depth: int
    import_info: ImportInfo | None = None


class CrossFileExtractor:
    """
    Extract code symbols with their cross-file dependencies.

    This class uses ImportResolver to build an understanding of the project's
    import structure, then extracts requested symbols along with the symbols
    they depend on from other files.

    Example:
        >>> extractor = CrossFileExtractor("/myproject")
        >>> result = extractor.extract("views.py", "handle_request")
        >>> if result.success:
        ...     print(result.combined_code)
        ...     print(f"Extracted {result.total_symbols} symbols")

    Depth Control:
    - depth=0: Only the target symbol (no dependencies)
    - depth=1: Target + direct imports used
    - depth=2: Target + direct + transitive imports
    - depth=3+: Continue following the chain

    The default depth=2 is usually sufficient for most refactoring tasks.

    """

    # Default maximum depth to prevent infinite loops
    MAX_DEPTH = 10

    def __init__(self, project_root: str | Path):
        """
        Initialize the cross-file extractor.

        Args:
            project_root: Absolute path to the project root
        """
        self.project_root = Path(project_root).resolve()
        self.resolver = ImportResolver(project_root)
        self._built = False
        self._file_cache: dict[str, str] = {}  # file_path -> source code
        self._ast_cache: dict[str, ast.AST] = {}  # file_path -> parsed AST

    def build(self) -> bool:
        """
        Build the import graph for the project.

        Must be called before extract(). Can be called multiple times
        to refresh if files have changed.

        Returns:
            True if build succeeded, False otherwise
        """
        result = self.resolver.build()
        self._built = result.success or len(result.warnings) > 0
        self._file_cache.clear()
        self._ast_cache.clear()
        return self._built

    def extract(
        self,
        file_path: str,
        symbol_name: str,
        depth: int = 2,
        include_stdlib: bool = False,
        confidence_decay_factor: float = DEFAULT_CONFIDENCE_DECAY_FACTOR,
    ) -> ExtractionResult:
        """
        Extract a symbol with its cross-file dependencies.

        Args:
            file_path: Path to the file containing the symbol (relative to project root)
            symbol_name: Name of the function/class to extract
            depth: How many levels of imports to follow (default: 2)
            include_stdlib: Whether to include stdlib symbols (default: False)
            confidence_decay_factor: Decay factor for confidence calculation (default: 0.9)
                                    Formula: C_effective = 1.0 × decay_factor^depth

        Returns:
            ExtractionResult with extracted code and metadata, including confidence scores
        """
        if not self._built:
            if not self.build():
                return ExtractionResult(success=False, errors=["Failed to build import graph"])

        result = ExtractionResult()
        # [20251216_FEATURE] v2.5.0 - Store decay factor for confidence calculation
        result.confidence_decay_factor = confidence_decay_factor

        # Normalize file path
        if os.path.isabs(file_path):
            abs_path = Path(file_path)
        else:
            abs_path = self.project_root / file_path

        abs_path = abs_path.resolve()

        if not abs_path.exists():
            return ExtractionResult(success=False, errors=[f"File not found: {file_path}"])

        # Get module name for this file
        try:
            os.path.relpath(abs_path, self.project_root)
        except ValueError:
            # [20251214_BUGFIX] Handle Windows short-path vs long-path mismatches gracefully
            pass

        module_name = self.resolver.file_to_module.get(str(abs_path))

        if not module_name:
            # Try to compute it
            module_name = self._path_to_module(abs_path)

        # Find the target symbol
        target_symbol = self._find_symbol_in_file(str(abs_path), symbol_name)

        if not target_symbol:
            return ExtractionResult(
                success=False,
                errors=[f"Symbol '{symbol_name}' not found in {file_path}"],
            )

        # [20251216_FEATURE] v2.5.0 - Target has depth 0 and confidence 1.0
        target_symbol.depth = 0
        target_symbol.confidence = 1.0

        result.target = target_symbol
        result.files_touched.add(str(abs_path))

        # Limit depth
        depth = min(depth, self.MAX_DEPTH)

        # BFS to gather dependencies
        if depth > 0:
            self._gather_dependencies(
                target_symbol,
                module_name,
                depth,
                result,
                include_stdlib,
            )

        # Generate combined code
        self._generate_combined_code(result)

        # [20251216_FEATURE] v2.5.0 - Add warning if low confidence symbols found
        if result.has_low_confidence_symbols:
            low_conf_symbols = result.get_low_confidence_symbols()
            result.warnings.append(
                f"⚠️ {result.low_confidence_count} symbol(s) have low confidence "
                f"(below {DEFAULT_LOW_CONFIDENCE_THRESHOLD}): "
                f"{', '.join(s.name for s in low_conf_symbols[:5])}" + ("..." if len(low_conf_symbols) > 5 else "")
            )

        result.success = len(result.errors) == 0
        return result

    def extract_multiple(
        self,
        targets: list[tuple[str, str]],
        depth: int = 2,
        include_stdlib: bool = False,
    ) -> ExtractionResult:
        """
        Extract multiple symbols with shared dependencies.

        Args:
            targets: List of (file_path, symbol_name) tuples
            depth: How many levels of imports to follow
            include_stdlib: Whether to include stdlib symbols

        Returns:
            ExtractionResult with all extracted code combined
        """
        if not self._built:
            if not self.build():
                return ExtractionResult(success=False, errors=["Failed to build import graph"])

        combined_result = ExtractionResult()
        all_dependencies: set[ExtractedSymbol] = set()
        primary_targets: list[ExtractedSymbol] = []

        for file_path, symbol_name in targets:
            single_result = self.extract(file_path, symbol_name, depth, include_stdlib)

            if not single_result.success:
                combined_result.errors.extend(single_result.errors)
                continue

            if single_result.target:
                primary_targets.append(single_result.target)

            for dep in single_result.dependencies:
                all_dependencies.add(dep)

            combined_result.files_touched.update(single_result.files_touched)
            combined_result.depth_reached = max(combined_result.depth_reached, single_result.depth_reached)

        # Remove primary targets from dependencies
        for target in primary_targets:
            all_dependencies.discard(target)

        combined_result.dependencies = list(all_dependencies)

        # Set target to first one if any
        if primary_targets:
            combined_result.target = primary_targets[0]
            # Add additional targets to dependencies
            for target in primary_targets[1:]:
                combined_result.dependencies.append(target)

        self._generate_combined_code(combined_result)
        combined_result.success = len(combined_result.errors) == 0

        return combined_result

    def _path_to_module(self, file_path: Path) -> str:
        """Convert a file path to a module name."""
        try:
            rel_path = file_path.relative_to(self.project_root)
        except ValueError:
            return file_path.stem

        parts = list(rel_path.parts)
        if parts[-1].endswith(".py"):
            parts[-1] = parts[-1][:-3]
        if parts[-1] == "__init__":
            parts = parts[:-1]

        return ".".join(parts) if parts else "__root__"

    def _get_file_source(self, file_path: str) -> str | None:
        """Get source code for a file, with caching."""
        if file_path in self._file_cache:
            return self._file_cache[file_path]

        try:
            with open(file_path, encoding="utf-8") as f:
                source = f.read()
            self._file_cache[file_path] = source
            return source
        except Exception:
            return None

    def _get_file_ast(self, file_path: str) -> ast.AST | None:
        """Get parsed AST for a file, with caching."""
        if file_path in self._ast_cache:
            return self._ast_cache[file_path]

        source = self._get_file_source(file_path)
        if not source:
            return None

        try:
            tree = ast.parse(source)
            self._ast_cache[file_path] = tree
            return tree
        except SyntaxError:
            return None

    def _find_symbol_in_file(self, file_path: str, symbol_name: str) -> ExtractedSymbol | None:
        """
        Find and extract a symbol from a file.

        Args:
            file_path: Absolute path to the file
            symbol_name: Name of the symbol to find

        Returns:
            ExtractedSymbol if found, None otherwise
        """
        source = self._get_file_source(file_path)
        if not source:
            return None

        tree = self._get_file_ast(file_path)
        if not tree:
            return None

        # Handle method names (ClassName.method_name)
        if "." in symbol_name:
            class_name, method_name = symbol_name.split(".", 1)
            return self._extract_method(file_path, source, tree, class_name, method_name)

        # Look for function or class
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == symbol_name:
                    return self._extract_function(file_path, source, node)

            elif isinstance(node, ast.ClassDef):
                if node.name == symbol_name:
                    return self._extract_class(file_path, source, node)

        return None

    def _extract_function(
        self,
        file_path: str,
        source: str,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> ExtractedSymbol:
        """Extract a function definition."""
        lines = source.split("\n")
        start_line = node.lineno - 1  # 0-indexed
        end_line = getattr(node, "end_lineno", None)

        if end_line:
            code = "\n".join(lines[start_line:end_line])
        else:
            # Fallback: extract until next def/class or end of file
            code = self._extract_to_next_definition(lines, start_line)

        module = self._path_to_module(Path(file_path))

        # Analyze dependencies (names used in the function)
        deps = self._analyze_symbol_dependencies(node)

        return ExtractedSymbol(
            name=node.name,
            symbol_type=("async_function" if isinstance(node, ast.AsyncFunctionDef) else "function"),
            module=module,
            file=file_path,
            code=code,
            line=node.lineno,
            end_line=end_line,
            dependencies=deps,
        )

    def _extract_class(self, file_path: str, source: str, node: ast.ClassDef) -> ExtractedSymbol:
        """Extract a class definition."""
        lines = source.split("\n")
        start_line = node.lineno - 1
        end_line = getattr(node, "end_lineno", None)

        if end_line:
            code = "\n".join(lines[start_line:end_line])
        else:
            code = self._extract_to_next_definition(lines, start_line)

        module = self._path_to_module(Path(file_path))
        deps = self._analyze_symbol_dependencies(node)

        return ExtractedSymbol(
            name=node.name,
            symbol_type="class",
            module=module,
            file=file_path,
            code=code,
            line=node.lineno,
            end_line=end_line,
            dependencies=deps,
        )

    def _extract_method(
        self,
        file_path: str,
        source: str,
        tree: ast.AST,
        class_name: str,
        method_name: str,
    ) -> ExtractedSymbol | None:
        """Extract a method from a class."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if item.name == method_name:
                            lines = source.split("\n")
                            start_line = item.lineno - 1
                            end_line = getattr(item, "end_lineno", None)

                            if end_line:
                                code = "\n".join(lines[start_line:end_line])
                            else:
                                code = self._extract_to_next_definition(lines, start_line)

                            module = self._path_to_module(Path(file_path))
                            deps = self._analyze_symbol_dependencies(item)

                            return ExtractedSymbol(
                                name=f"{class_name}.{method_name}",
                                symbol_type="method",
                                module=module,
                                file=file_path,
                                code=code,
                                line=item.lineno,
                                end_line=end_line,
                                dependencies=deps,
                            )
        return None

    def _extract_to_next_definition(self, lines: list[str], start_line: int) -> str:
        """Extract code from start_line until the next definition or end of file."""
        result_lines = [lines[start_line]]
        indent = len(lines[start_line]) - len(lines[start_line].lstrip())

        for i in range(start_line + 1, len(lines)):
            line = lines[i]
            stripped = line.lstrip()

            # Empty or comment line - include
            if not stripped or stripped.startswith("#"):
                result_lines.append(line)
                continue

            # Check if this is a new top-level definition
            line_indent = len(line) - len(stripped)
            if line_indent <= indent and (
                stripped.startswith("def ") or stripped.startswith("async def ") or stripped.startswith("class ")
            ):
                break

            result_lines.append(line)

        return "\n".join(result_lines)

    def _analyze_symbol_dependencies(self, node: ast.AST) -> set[str]:
        """
        Analyze an AST node to find names it depends on.

        This finds all Name nodes that could reference imported symbols.
        """
        dependencies = set()

        # Names that are defined locally within this symbol
        local_names = set()

        for child in ast.walk(node):
            # Track local definitions
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
                local_names.add(child.id)
            elif isinstance(child, ast.arg):
                local_names.add(child.arg)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                local_names.add(child.name)
            elif isinstance(child, ast.ClassDef):
                local_names.add(child.name)

            # Track uses
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                dependencies.add(child.id)
            elif isinstance(child, ast.Attribute):
                # Get the root name (e.g., 'os' from 'os.path.join')
                root = self._get_attribute_root(child)
                if root:
                    dependencies.add(root)

        # Remove local names and builtins
        dependencies -= local_names
        dependencies -= self._get_builtins()

        return dependencies

    def _get_attribute_root(self, node: ast.Attribute) -> str | None:
        """Get the root name of an attribute chain."""
        current = node
        while isinstance(current, ast.Attribute):
            current = current.value
        if isinstance(current, ast.Name):
            return current.id
        return None

    def _get_builtins(self) -> set[str]:
        """Get set of Python builtin names."""
        import builtins

        return set(dir(builtins))

    def _gather_dependencies(
        self,
        target: ExtractedSymbol,
        target_module: str,
        max_depth: int,
        result: ExtractionResult,
        include_stdlib: bool,
    ) -> None:
        """
        BFS to gather all dependencies up to max_depth.
        """
        # Queue: (symbol_name, module, depth)
        queue = deque()
        visited: set[tuple[str, str]] = set()

        # Seed with target's dependencies
        for dep_name in target.dependencies:
            queue.append(
                DependencyNode(
                    symbol_name=dep_name,
                    module=target_module,
                    depth=1,
                )
            )

        visited.add((target_module, target.name))

        while queue:
            node = queue.popleft()

            if node.depth > max_depth:
                continue

            result.depth_reached = max(result.depth_reached, node.depth)

            # Try to resolve this dependency
            resolved_module, symbol_def = self.resolver.resolve_symbol(node.module, node.symbol_name)

            if not resolved_module or not symbol_def:
                # Could be a stdlib or external dependency
                continue

            # Skip if already visited
            if (resolved_module, node.symbol_name) in visited:
                continue
            visited.add((resolved_module, node.symbol_name))

            # Skip stdlib if not requested
            if not include_stdlib and self._is_stdlib_module(resolved_module):
                continue

            # Get the file path
            file_path = self.resolver.module_to_file.get(resolved_module)
            if not file_path:
                continue

            # Extract the symbol
            extracted = self._find_symbol_in_file(file_path, symbol_def.name)
            if not extracted:
                # Try looking for the original name if it was a method
                extracted = self._find_symbol_in_file(file_path, node.symbol_name)

            if extracted:
                # [20251216_FEATURE] v2.5.0 - Set depth and calculate confidence with decay
                extracted.depth = node.depth
                extracted.confidence = calculate_confidence(node.depth, result.confidence_decay_factor)
                # Track low confidence symbols
                if extracted.confidence < DEFAULT_LOW_CONFIDENCE_THRESHOLD:
                    result.low_confidence_count += 1

                result.dependencies.append(extracted)
                result.files_touched.add(file_path)

                # Add this symbol's dependencies to the queue
                if node.depth < max_depth:
                    for sub_dep in extracted.dependencies:
                        if (resolved_module, sub_dep) not in visited:
                            queue.append(
                                DependencyNode(
                                    symbol_name=sub_dep,
                                    module=resolved_module,
                                    depth=node.depth + 1,
                                )
                            )

    def _is_stdlib_module(self, module_name: str) -> bool:
        """Check if a module is from the standard library."""

        # Common stdlib modules
        stdlib_prefixes = {
            "os",
            "sys",
            "io",
            "re",
            "json",
            "math",
            "random",
            "collections",
            "itertools",
            "functools",
            "typing",
            "pathlib",
            "datetime",
            "time",
            "logging",
            "warnings",
            "unittest",
            "pytest",
            "abc",
            "contextlib",
            "dataclasses",
            "enum",
            "copy",
            "pickle",
            "csv",
            "xml",
            "html",
            "http",
            "urllib",
            "socket",
            "email",
            "base64",
            "hashlib",
            "hmac",
            "secrets",
            "threading",
            "multiprocessing",
            "subprocess",
            "asyncio",
            "concurrent",
            "queue",
            "sched",
            "select",
            "signal",
        }

        root = module_name.split(".")[0]
        return root in stdlib_prefixes

    def _generate_combined_code(self, result: ExtractionResult) -> None:
        """
        Generate the combined code output with dependencies first.
        """
        if not result.target and not result.dependencies:
            result.combined_code = ""
            return

        # Sort dependencies by module to group related code
        sorted_deps = sorted(result.dependencies, key=lambda x: (x.module, x.line))

        # Collect import statements needed
        modules_used = set()
        if result.target:
            modules_used.add(result.target.module)
        for dep in sorted_deps:
            modules_used.add(dep.module)

        # Generate imports header
        imports = []
        for module in sorted(modules_used):
            if module != result.target.module if result.target else True:
                imports.append(f"# From {module}")
        result.module_imports = imports

        # Combine code
        code_parts = []

        # Add a header comment
        code_parts.append("# ===== Cross-File Extraction =====")
        if result.target:
            code_parts.append(f"# Target: {result.target.name} from {result.target.module}")
        code_parts.append(f"# Dependencies: {len(result.dependencies)}")
        code_parts.append(f"# Files: {len(result.files_touched)}")
        code_parts.append("")

        # Group by module
        by_module: dict[str, list[ExtractedSymbol]] = {}
        for dep in sorted_deps:
            if dep.module not in by_module:
                by_module[dep.module] = []
            by_module[dep.module].append(dep)

        # Add dependencies first
        for module in sorted(by_module.keys()):
            if result.target and module == result.target.module:
                continue  # Will add with target

            code_parts.append(f"# ----- From {module} -----")
            for dep in by_module[module]:
                code_parts.append(dep.code)
                code_parts.append("")

        # Add target (and any same-module dependencies)
        if result.target:
            code_parts.append(f"# ----- Target: {result.target.module} -----")

            # Add same-module dependencies first
            if result.target.module in by_module:
                for dep in by_module[result.target.module]:
                    code_parts.append(dep.code)
                    code_parts.append("")

            code_parts.append(result.target.code)

        result.combined_code = "\n".join(code_parts)

    def get_symbol_dependencies(
        self,
        file_path: str,
        symbol_name: str,
    ) -> set[str]:
        """
        Get the set of names a symbol depends on (without extraction).

        Args:
            file_path: Path to the file
            symbol_name: Name of the symbol

        Returns:
            Set of dependency names
        """
        if not self._built:
            self.build()

        if os.path.isabs(file_path):
            abs_path = Path(file_path)
        else:
            abs_path = self.project_root / file_path

        symbol = self._find_symbol_in_file(str(abs_path), symbol_name)
        if symbol:
            return symbol.dependencies
        return set()

    def get_dependents(
        self,
        file_path: str,
        symbol_name: str,
    ) -> list[tuple[str, str]]:
        """
        Find symbols that depend on the given symbol.

        Args:
            file_path: Path to the file containing the symbol
            symbol_name: Name of the symbol

        Returns:
            List of (module, symbol_name) tuples for symbols that use this one
        """
        if not self._built:
            self.build()

        if os.path.isabs(file_path):
            abs_path = Path(file_path)
        else:
            abs_path = self.project_root / file_path

        module_name = self.resolver.file_to_module.get(str(abs_path))
        if not module_name:
            return []

        # Find modules that import this module
        importers = self.resolver.get_importers(module_name)

        dependents = []
        for importer_module in importers:
            importer_file = self.resolver.module_to_file.get(importer_module)
            if not importer_file:
                continue

            # Check imports from this module
            imports = self.resolver.imports.get(importer_module, [])
            for imp in imports:
                if imp.module == module_name and imp.name == symbol_name:
                    # Found a direct import - find what uses it
                    symbols = self.resolver.symbols.get(importer_module, {})
                    for sym_name, _sym_def in symbols.items():
                        # Check if this symbol uses the imported name
                        sym_obj = self._find_symbol_in_file(importer_file, sym_name)
                        if sym_obj and imp.effective_name in sym_obj.dependencies:
                            dependents.append((importer_module, sym_name))

        return dependents
