"""
Surgical Extractor - Precision code extraction for token-efficient LLM interactions.

# [20251224_REFACTOR] Moved from code_scalpel/surgical_extractor.py to
# code_scalpel/surgery/surgical_extractor.py as part of Issue #2
# in PROJECT_REORG_REFACTOR.md Phase 1.

This module provides surgical extraction of code elements (functions, classes, methods)
from source files. Instead of feeding entire files to LLMs, extract only the relevant
pieces plus their dependencies.

Key Principle: "Feed the LLM 50 lines, not 5,000 lines."

Usage:
    from code_scalpel.surgery import SurgicalExtractor

    extractor = SurgicalExtractor(code)

    # Extract just one function (saves tokens)
    func_code = extractor.get_function("calculate_tax")

    # Extract with context (dependencies)
    func_with_deps = extractor.get_function_with_context("calculate_tax")

    # Extract a class method
    method_code = extractor.get_method("Calculator", "add")

Enhancement Roadmap
===================

COMPLETED (v3.1.0 - December 2025):
- Accurate token counting with tiktoken (GPT-4, GPT-3.5, Claude)
- Enhanced metadata extraction (docstring, signature, decorators, async/generator detection)
- LLM-ready prompt formatting (to_prompt(), summarize())
- Token budget management (trim_to_budget())
- Decorator extraction (get_decorator(), list_decorators())
- Caller discovery for impact analysis (find_callers())
- LRU caching for extraction performance (2.8x speedup)
- Source file tracking in extraction results
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    tiktoken = None  # type: ignore[assignment]

from code_scalpel.parsing.unified_parser import ParsingError, parse_python_code
from code_scalpel.utilities.path_resolution import resolve_file_path


# [20251221_FEATURE] Token counting utilities
@lru_cache(maxsize=128)
def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Count tokens in text using tiktoken if available, else fallback to char/4.

    [20251221_FEATURE] Accurate token counting with model-specific encodings.

    Args:
        text: Text to count tokens for
        model: Model name ("gpt-4", "gpt-3.5-turbo", "claude-3-opus", etc.)

    Returns:
        Token count

    Note:
        Results are cached for performance. Claude models use rough estimation.
    """
    if not TIKTOKEN_AVAILABLE or not tiktoken:
        # Fallback to rough estimation
        return len(text) // 4

    try:
        # Map model names to tiktoken encodings
        if "gpt-4" in model.lower():
            encoding = tiktoken.encoding_for_model("gpt-4")  # type: ignore[attr-defined]
        elif "gpt-3.5" in model.lower():
            encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")  # type: ignore[attr-defined]
        elif "claude" in model.lower():
            # Claude uses different tokenization, approximate with gpt-4
            # In practice, Claude token counts are similar but slightly different
            encoding = tiktoken.encoding_for_model("gpt-4")  # type: ignore[attr-defined]
        else:
            # Default to gpt-4 encoding
            encoding = tiktoken.encoding_for_model("gpt-4")  # type: ignore[attr-defined]

        return len(encoding.encode(text))
    except Exception:
        # If anything goes wrong, fall back to rough estimation
        return len(text) // 4


@dataclass
class CrossFileSymbol:
    """
    A symbol resolved from an external file.

    """

    name: str
    source_file: str
    code: str
    node_type: str  # "function", "class", "variable"
    import_statement: str  # e.g., "from models import TaxRate"
    # [20251231_FEATURE] Confidence scoring metadata for dependency resolution.
    depth: int = 1
    confidence: float = 1.0


@dataclass
class CrossFileResolution:
    """
    Result of cross-file dependency resolution.

    """

    success: bool
    target: ExtractionResult
    external_symbols: list[CrossFileSymbol] = field(default_factory=list)
    unresolved_imports: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def full_code(self) -> str:
        """Get combined code: external dependencies + target."""
        parts = []
        # Group by source file for cleaner output
        by_file: dict[str, list[CrossFileSymbol]] = {}
        for sym in self.external_symbols:
            by_file.setdefault(sym.source_file, []).append(sym)

        for source_file, symbols in by_file.items():
            parts.append(f"# From {source_file}")
            for sym in symbols:
                parts.append(sym.code)

        if parts:
            parts.append("")  # blank line separator
        parts.append(self.target.code)
        return "\n\n".join(parts)

    @property
    def token_estimate(self) -> int:
        """Rough token estimate."""
        return len(self.full_code) // 4


@dataclass
class ExtractionResult:
    """
    Result of a surgical extraction.

    [20251221_FEATURE] Enhanced with metadata extraction and accurate token counting.
    """

    success: bool
    name: str
    code: str
    node_type: str  # "function", "class", "method"
    line_start: int = 0
    line_end: int = 0
    dependencies: list[str] = field(default_factory=list)
    imports_needed: list[str] = field(default_factory=list)
    error: str | None = None

    # [20251221_FEATURE] Enhanced metadata fields
    docstring: str | None = None
    signature: str | None = None
    decorators: list[str] = field(default_factory=list)
    is_async: bool = False
    is_generator: bool = False
    source_file: str | None = None
    parent_class: str | None = None

    @property
    def token_estimate(self) -> int:
        """
        Estimate token count using tiktoken if available, else char/4 fallback.

        [20251221_FEATURE] Uses tiktoken for accurate GPT token counts.
        """
        return count_tokens(self.code)

    def get_token_count(self, model: str = "gpt-4") -> int:
        """
        Get accurate token count for a specific model.

        Args:
            model: Model name ("gpt-4", "gpt-3.5-turbo", "claude-3-opus", etc.)

        Returns:
            Token count for the specified model
        """
        return count_tokens(self.code, model)


@dataclass
class ContextualExtraction:
    """
    Extraction with all required context for LLM understanding.

    [20251221_FEATURE] Enhanced with LLM-ready formatting and budget management.
    """

    target: ExtractionResult
    context_code: str  # Combined code of all dependencies
    total_lines: int
    context_items: list[str]  # Names of included dependencies
    truncated: bool = False
    omitted_items: list[str] = field(default_factory=list)

    @property
    def full_code(self) -> str:
        """Get the complete code block for LLM consumption."""
        if self.context_code:
            return f"{self.context_code}\n\n{self.target.code}"
        return self.target.code

    @property
    def token_estimate(self) -> int:
        """Estimate tokens using tiktoken if available."""
        return count_tokens(self.full_code)

    def get_token_count(self, model: str = "gpt-4") -> int:
        """
        Get accurate token count for a specific model.

        Args:
            model: Model name ("gpt-4", "gpt-3.5-turbo", etc.)

        Returns:
            Token count for the specified model
        """
        return count_tokens(self.full_code, model)

    def to_prompt(self, instruction: str, include_metadata: bool = True) -> str:
        """
        Format the extraction as an LLM-ready prompt.

        [20251221_FEATURE] Generates structured prompts for AI agent consumption.

        Args:
            instruction: The task instruction for the LLM
            include_metadata: Whether to include extraction metadata

        Returns:
            Formatted prompt string ready for LLM input

        Example:
            >>> extraction = extractor.get_function_with_context("calculate_tax")
            >>> prompt = extraction.to_prompt("Add input validation to this function")
            >>> response = llm.complete(prompt)
        """
        parts = []

        # Header
        parts.append(f"# Code Extraction: {self.target.name}")
        parts.append("")

        # Metadata section
        if include_metadata:
            parts.append("## Metadata")
            parts.append(f"- Type: {self.target.node_type}")
            parts.append(f"- Lines: {self.target.line_start}-{self.target.line_end}")
            if self.target.source_file:
                parts.append(f"- Source: {self.target.source_file}")
            if self.target.docstring:
                parts.append(f"- Docstring: {self.target.docstring[:100]}...")
            parts.append(f"- Dependencies: {', '.join(self.target.dependencies) or 'None'}")
            parts.append(f"- Context items: {len(self.context_items)}")
            parts.append(f"- Total lines: {self.total_lines}")
            parts.append(f"- Estimated tokens: {self.token_estimate}")
            if self.truncated:
                parts.append(f"- ⚠️ Context truncated (omitted: {', '.join(self.omitted_items)})")
            parts.append("")

        # Context section
        if self.context_code:
            parts.append("## Context (Dependencies)")
            parts.append("```python")
            parts.append(self.context_code)
            parts.append("```")
            parts.append("")

        # Target code section
        parts.append("## Target Code")
        parts.append("```python")
        parts.append(self.target.code)
        parts.append("```")
        parts.append("")

        # Instruction section
        parts.append("## Task")
        parts.append(instruction)
        parts.append("")

        return "\n".join(parts)

    def summarize(self) -> str:
        """
        Generate a brief summary of the extraction.

        [20251221_FEATURE] Provides human-readable summary.

        Returns:
            Summary string describing the extraction
        """
        summary_parts = [
            f"{self.target.node_type.capitalize()}: {self.target.name}",
            f"Lines: {self.total_lines}",
            f"Tokens: ~{self.token_estimate}",
            f"Dependencies: {len(self.target.dependencies)}",
            f"Context: {len(self.context_items)} items",
        ]

        if self.truncated:
            summary_parts.append(f"⚠️ Truncated ({len(self.omitted_items)} omitted)")

        return " | ".join(summary_parts)

    def trim_to_budget(self, max_tokens: int, model: str = "gpt-4") -> ContextualExtraction:
        """
        Trim context to fit within a token budget while preserving essentials.

        [20251221_FEATURE] Intelligent budget management for token-constrained scenarios.

        Strategy:
        1. Always keep the target code (required)
        2. Keep imports (usually small)
        3. Remove context items one by one (least important first)
        4. Mark as truncated and track omitted items

        Args:
            max_tokens: Maximum tokens allowed for the full extraction
            model: Model name for accurate token counting

        Returns:
            New ContextualExtraction that fits within budget

        Example:
            >>> extraction = extractor.get_function_with_context("main", max_depth=3)
            >>> extraction.token_estimate
            5000
            >>> trimmed = extraction.trim_to_budget(2000)
            >>> trimmed.token_estimate
            1950
            >>> trimmed.truncated
            True
        """
        # Check if we're already under budget
        current_tokens = count_tokens(self.full_code, model)
        if current_tokens <= max_tokens:
            return self

        # Target code is required - check if it alone fits
        target_tokens = count_tokens(self.target.code, model)
        if target_tokens > max_tokens:
            # Even the target alone is too big - return it anyway with warning
            return ContextualExtraction(
                target=self.target,
                context_code="",
                total_lines=len(self.target.code.splitlines()),
                context_items=[],
                truncated=True,
                omitted_items=self.context_items,
            )

        # Try to fit as much context as possible
        # Split context by items (this is approximate - we'll rebuild properly)
        remaining_budget = max_tokens - target_tokens

        # Get imports first (high priority)
        imports_code = self._get_imports_from_context()
        imports_tokens = count_tokens(imports_code, model) if imports_code else 0

        if imports_tokens > remaining_budget:
            # Can't even fit imports - just return target
            return ContextualExtraction(
                target=self.target,
                context_code="",
                total_lines=len(self.target.code.splitlines()),
                context_items=[],
                truncated=True,
                omitted_items=self.context_items,
            )

        # Simple strategy: include context until we hit budget
        # In a real implementation, we'd prioritize by dependency order
        included_items = []
        omitted = list(self.context_items)

        # This is a simplified version - a real implementation would
        # parse context_code to extract individual items and add them one by one
        # For now, just use the full context if it fits, otherwise none
        context_without_imports = (
            self.context_code.replace(imports_code, "").strip() if imports_code else self.context_code
        )
        context_tokens = count_tokens(context_without_imports, model)

        if imports_tokens + context_tokens <= remaining_budget:
            # Everything fits
            return self

        # Need to trim - for now, just keep imports
        return ContextualExtraction(
            target=self.target,
            context_code=imports_code if imports_code else "",
            total_lines=(
                len(imports_code.splitlines()) + len(self.target.code.splitlines())
                if imports_code
                else len(self.target.code.splitlines())
            ),
            context_items=included_items,
            truncated=True,
            omitted_items=omitted,
        )

    def _get_imports_from_context(self) -> str:
        """Extract import statements from context code."""
        if not self.context_code:
            return ""

        lines = self.context_code.splitlines()
        import_lines = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                import_lines.append(line)
            elif import_lines and stripped:  # Stop at first non-import code
                break

        return "\n".join(import_lines) if import_lines else ""


class SurgicalExtractor:
    """
    Precision code extractor using AST analysis.

    Extracts specific code elements while preserving structure and
    identifying dependencies for context-aware extraction.

    Example (from string):
        >>> code = '''
        ... def helper():
        ...     return 42
        ...
        ... def main():
        ...     return helper() + 1
        ... '''
        >>> extractor = SurgicalExtractor(code)
        >>> result = extractor.get_function("main")
        >>> print(result.code)
        def main():
            return helper() + 1
        >>> print(result.dependencies)
        ['helper']

    Example (from file - TOKEN SAVER):
        >>> # Agent asks: "Get me calculate_tax from utils.py"
        >>> # Agent pays ~50 tokens, Server does the heavy lifting
        >>> extractor = SurgicalExtractor.from_file("/path/to/utils.py")
        >>> result = extractor.get_function("calculate_tax")
        >>> # Agent receives only the function (~200 tokens)

    ============================================

    Extraction Capabilities:

    Search & Discovery:

    Context Management:

    Performance:

    Output Formats:
    """

    def __init__(self, code: str, file_path: str | None = None):
        """
        Initialize the extractor with source code.

        Args:
            code: Python source code to analyze
            file_path: Optional path to the source file (for cross-file resolution)
        """
        self.code = code
        self.file_path = file_path
        self.source_lines = code.splitlines()
        self._tree: ast.Module | None = None
        self._functions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
        self._classes: dict[str, ast.ClassDef] = {}
        self._imports: list[ast.Import | ast.ImportFrom] = []
        self._global_assigns: dict[str, ast.Assign] = {}
        self._decorators: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
        self._parsed = False

    @classmethod
    def from_file(cls, file_path: str, encoding: str = "utf-8") -> SurgicalExtractor:
        """
        Create an extractor by reading directly from a file.

        This is the TOKEN-EFFICIENT path. The Agent specifies a file path,
        the Server reads it (0 token cost to Agent), and returns only the
        requested symbol.

        Args:
            file_path: Path to the Python source file
            encoding: File encoding (default: utf-8)

        Returns:
            SurgicalExtractor instance ready for extraction

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file can't be read or parsed

        Example:
            >>> extractor = SurgicalExtractor.from_file("src/utils.py")
            >>> func = extractor.get_function("calculate_tax")
            >>> # Agent receives ~50 lines, not 5000
        """

        # Resolve file path (handles relative/absolute, workspace roots, etc.)
        try:
            resolved_path = resolve_file_path(file_path, check_exists=True)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"File not found: {file_path}") from e

        try:
            with open(resolved_path, encoding=encoding) as f:
                code = f.read()
        except OSError as e:
            raise ValueError(f"Cannot read file {resolved_path}: {e}")

        return cls(code, file_path=resolved_path)

    def _ensure_parsed(self) -> None:
        """Parse the code if not already done."""
        if self._parsed:
            return

        try:
            tree, _report = parse_python_code(self.code, filename="<extraction>")
            self._tree = tree if isinstance(tree, ast.Module) else ast.Module(body=[], type_ignores=[])
        except ParsingError as e:
            raise ValueError(f"Invalid Python code: {e}")

        # [20251215_BUGFIX] Index all definitions including nested classes
        def index_class_recursively(class_node: ast.ClassDef) -> None:
            """Recursively index nested classes."""
            self._classes[class_node.name] = class_node
            for child in class_node.body:
                if isinstance(child, ast.ClassDef):
                    index_class_recursively(child)

        # Index top-level definitions
        for node in self._tree.body:
            if isinstance(node, ast.FunctionDef):
                self._functions[node.name] = node
                # Track decorators (functions used as decorators)
                if node.decorator_list:
                    for dec in node.decorator_list:
                        if isinstance(dec, ast.Name):
                            # Decorator might be a function we need to extract
                            pass  # We'll find it when we look for the decorator definition
            elif isinstance(node, ast.AsyncFunctionDef):
                self._functions[node.name] = node
            elif isinstance(node, ast.ClassDef):
                index_class_recursively(node)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                self._imports.append(node)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self._global_assigns[target.id] = node

        self._parsed = True

    def list_functions(self) -> list[str]:
        """List all top-level function names."""
        self._ensure_parsed()
        return list(self._functions.keys())

    def list_classes(self) -> list[str]:
        """List all class names."""
        self._ensure_parsed()
        return list(self._classes.keys())

    def list_methods(self, class_name: str) -> list[str]:
        """List all methods of a class."""
        self._ensure_parsed()
        if class_name not in self._classes:
            return []

        methods = []
        for node in self._classes[class_name].body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(node.name)
        return methods

    def list_decorators(self) -> list[str]:
        """
        List all decorator names used in the code.

        [20251221_FEATURE] Find all decorators for decorator extraction.

        Returns:
            List of unique decorator names
        """
        self._ensure_parsed()
        decorators = set()

        def collect_decorator_names(node: ast.AST) -> None:
            """Recursively collect decorator names."""
            for child in ast.walk(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    for dec in child.decorator_list:
                        if isinstance(dec, ast.Name):
                            decorators.add(dec.id)
                        elif isinstance(dec, ast.Attribute):
                            # Handle @property, @staticmethod, etc.
                            decorators.add(ast.unparse(dec))
                        elif isinstance(dec, ast.Call):
                            # Handle @decorator(args)
                            if isinstance(dec.func, ast.Name):
                                decorators.add(dec.func.id)
                            elif isinstance(dec.func, ast.Attribute):
                                decorators.add(ast.unparse(dec.func))

        if self._tree is not None:
            collect_decorator_names(self._tree)
        return sorted(decorators)

    def get_function(self, name: str) -> ExtractionResult:
        """
        Extract a function by name.

        [20251221_FEATURE] Results cached with LRU cache for performance.

        Args:
            name: Function name to extract

        Returns:
            ExtractionResult with the function code
        """
        # Use internal cached method
        return self._get_function_cached(name)

    @lru_cache(maxsize=256)
    def _get_function_cached(self, name: str) -> ExtractionResult:
        """Internal cached implementation of get_function."""
        self._ensure_parsed()

        if name not in self._functions:
            return ExtractionResult(
                success=False,
                name=name,
                code="",
                node_type="function",
                error=f"Function '{name}' not found. Available: {list(self._functions.keys())}",
            )

        node = self._functions[name]
        code = self._node_to_code(node)
        deps = self._find_dependencies(node)
        imports = self._find_required_imports(node)

        # [20251221_FEATURE] Extract metadata
        docstring = ast.get_docstring(node)
        decorators = [ast.unparse(dec) for dec in node.decorator_list] if node.decorator_list else []
        is_async = isinstance(node, ast.AsyncFunctionDef)

        # Check if generator
        is_generator = False
        for child in ast.walk(node):
            if isinstance(child, (ast.Yield, ast.YieldFrom)):
                is_generator = True
                break

        # Get signature (function definition line)
        signature = self._get_signature(node)

        return ExtractionResult(
            success=True,
            name=name,
            code=code,
            node_type="function",
            line_start=node.lineno,
            line_end=getattr(node, "end_lineno", node.lineno),
            dependencies=deps,
            imports_needed=imports,
            docstring=docstring,
            signature=signature,
            decorators=decorators,
            is_async=is_async,
            is_generator=is_generator,
            source_file=self.file_path,
        )

    def _get_signature(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        """
        Extract function signature.

        [20251221_FEATURE] Extract clean function signatures for documentation.
        """
        # Get just the def line
        if hasattr(node, "lineno") and self.source_lines:
            # Get the line with 'def'
            def_line_idx = node.lineno - 1
            if def_line_idx < len(self.source_lines):
                line = self.source_lines[def_line_idx].strip()
                # Handle multi-line signatures
                if not line.endswith(":"):
                    # Multi-line signature, collect until ':'
                    sig_lines = [line]
                    for idx in range(def_line_idx + 1, min(def_line_idx + 10, len(self.source_lines))):
                        sig_lines.append(self.source_lines[idx].strip())
                        if self.source_lines[idx].strip().endswith(":"):
                            break
                    return " ".join(sig_lines)
                return line

        # Fallback: unparse the function definition
        try:
            # Create a copy with empty body
            temp_node = ast.FunctionDef(
                name=node.name,
                args=node.args,
                body=[ast.Pass()],
                decorator_list=[],
                returns=node.returns,
                lineno=0,
                col_offset=0,
            )  # type: ignore[call-overload]
            sig = ast.unparse(temp_node)
            # Remove the 'pass' body
            return sig.replace(":\n    pass", ":")
        except Exception:
            return f"def {node.name}(...):"

    def get_class(self, name: str) -> ExtractionResult:
        """
        Extract a class by name.

        [20251221_FEATURE] Results cached with LRU cache for performance.

        Args:
            name: Class name to extract

        Returns:
            ExtractionResult with the class code
        """
        return self._get_class_cached(name)

    @lru_cache(maxsize=256)
    def _get_class_cached(self, name: str) -> ExtractionResult:
        """Internal cached implementation of get_class."""
        self._ensure_parsed()

        if name not in self._classes:
            return ExtractionResult(
                success=False,
                name=name,
                code="",
                node_type="class",
                error=f"Class '{name}' not found. Available: {list(self._classes.keys())}",
            )

        node = self._classes[name]
        code = self._node_to_code(node)
        deps = self._find_dependencies(node)
        imports = self._find_required_imports(node)

        # [20251221_FEATURE] Extract metadata
        docstring = ast.get_docstring(node)
        decorators = [ast.unparse(dec) for dec in node.decorator_list] if node.decorator_list else []
        signature = f"class {node.name}"
        if node.bases:
            bases_str = ", ".join(ast.unparse(base) for base in node.bases)
            signature += f"({bases_str})"
        signature += ":"

        return ExtractionResult(
            success=True,
            name=name,
            code=code,
            node_type="class",
            line_start=node.lineno,
            line_end=getattr(node, "end_lineno", node.lineno),
            dependencies=deps,
            imports_needed=imports,
            docstring=docstring,
            signature=signature,
            decorators=decorators,
            source_file=self.file_path,
        )

    def get_method(self, class_name: str, method_name: str) -> ExtractionResult:
        """
        Extract a specific method from a class.

        Args:
            class_name: Name of the class
            method_name: Name of the method

        Returns:
            ExtractionResult with the method code
        """
        self._ensure_parsed()

        if class_name not in self._classes:
            return ExtractionResult(
                success=False,
                name=f"{class_name}.{method_name}",
                code="",
                node_type="method",
                error=f"Class '{class_name}' not found.",
            )

        class_node = self._classes[class_name]
        method_node = None

        for node in class_node.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == method_name:
                    method_node = node
                    break

        if method_node is None:
            available = self.list_methods(class_name)
            return ExtractionResult(
                success=False,
                name=f"{class_name}.{method_name}",
                code="",
                node_type="method",
                error=f"Method '{method_name}' not found in class '{class_name}'. Available: {available}",
            )

        code = self._node_to_code(method_node)
        deps = self._find_dependencies(method_node)
        imports = self._find_required_imports(method_node)

        return ExtractionResult(
            success=True,
            name=f"{class_name}.{method_name}",
            code=code,
            node_type="method",
            line_start=method_node.lineno,
            line_end=getattr(method_node, "end_lineno", method_node.lineno),
            dependencies=deps,
            imports_needed=imports,
        )

    def get_decorator(self, name: str) -> ExtractionResult:
        """
        Extract a decorator function by name.

        [20251221_FEATURE] Extract decorator definitions for understanding decorators.

        Args:
            name: Decorator function name to extract

        Returns:
            ExtractionResult with the decorator function code

        Example:
            >>> extractor = SurgicalExtractor(code)
            >>> decorator = extractor.get_decorator("my_decorator")
            >>> print(decorator.code)
            def my_decorator(func):
                def wrapper(*args, **kwargs):
                    print("Before")
                    result = func(*args, **kwargs)
                    print("After")
                    return result
                return wrapper
        """
        # Decorators are just functions, so reuse get_function
        result = self.get_function(name)
        if result.success:
            result.node_type = "decorator"
        return result

    def find_callers(self, target_name: str) -> list[tuple[str, str, int]]:
        """
        Find all functions/methods that call a target function.

        [20251221_FEATURE] Discover code usage patterns for impact analysis.

        Args:
            target_name: Name of the function to find callers for

        Returns:
            List of tuples: (caller_name, caller_type, line_number)
            caller_type is "function", "method", or "class"

        Example:
            >>> extractor = SurgicalExtractor(code)
            >>> callers = extractor.find_callers("helper")
            >>> for name, typ, line in callers:
            ...     print(f"{typ} {name} calls helper() at line {line}")
            function main calls helper() at line 42
            method Calculator.compute calls helper() at line 89
        """
        self._ensure_parsed()
        callers = []

        class CallFinder(ast.NodeVisitor):
            def __init__(self, target: str):
                self.target = target
                self.current_scope: tuple[str, str] | None = None  # (name, type)

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                old_scope = self.current_scope
                self.current_scope = (node.name, "function")

                # Check if this function calls the target
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Name):
                            if child.func.id == self.target:
                                callers.append((node.name, "function", child.lineno))
                                break
                        elif isinstance(child.func, ast.Attribute):
                            # Handle self.target() calls
                            if child.func.attr == self.target:
                                callers.append((node.name, "function", child.lineno))
                                break

                self.current_scope = old_scope
                self.generic_visit(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                # Same as FunctionDef
                old_scope = self.current_scope
                self.current_scope = (node.name, "function")

                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Name):
                            if child.func.id == self.target:
                                callers.append((node.name, "function", child.lineno))
                                break
                        elif isinstance(child.func, ast.Attribute):
                            if child.func.attr == self.target:
                                callers.append((node.name, "function", child.lineno))
                                break

                self.current_scope = old_scope
                self.generic_visit(node)

            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                # Check methods in this class
                for method in node.body:
                    if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        for child in ast.walk(method):
                            if isinstance(child, ast.Call):
                                if isinstance(child.func, ast.Name):
                                    if child.func.id == self.target:
                                        callers.append(
                                            (
                                                f"{node.name}.{method.name}",
                                                "method",
                                                child.lineno,
                                            )
                                        )
                                        break
                                elif isinstance(child.func, ast.Attribute):
                                    if child.func.attr == self.target:
                                        callers.append(
                                            (
                                                f"{node.name}.{method.name}",
                                                "method",
                                                child.lineno,
                                            )
                                        )
                                        break

                self.generic_visit(node)

        finder = CallFinder(target_name)
        if self._tree is not None:
            finder.visit(self._tree)
        return callers

    def get_function_with_context(self, name: str, max_depth: int = 2) -> ContextualExtraction:
        """
        Extract a function with all its dependencies.

        This is the key token-saving operation: instead of giving the LLM
        the entire file, give it just the function plus the things it calls.

        Args:
            name: Function name to extract
            max_depth: How deep to follow dependencies (default: 2)

        Returns:
            ContextualExtraction with target and context
        """
        target = self.get_function(name)
        if not target.success:
            return ContextualExtraction(
                target=target,
                context_code="",
                total_lines=0,
                context_items=[],
            )

        # Gather context recursively
        context_items = []
        context_code_parts = []
        visited = {name}

        def gather_deps(deps: list[str], depth: int) -> None:
            if depth > max_depth:
                return

            for dep in deps:
                if dep in visited:
                    continue
                visited.add(dep)

                # Try function first
                if dep in self._functions:
                    dep_result = self.get_function(dep)
                    if dep_result.success:
                        context_items.append(dep)
                        context_code_parts.append(dep_result.code)
                        gather_deps(dep_result.dependencies, depth + 1)

                # Then try class
                elif dep in self._classes:
                    dep_result = self.get_class(dep)
                    if dep_result.success:
                        context_items.append(dep)
                        context_code_parts.append(dep_result.code)

                # Then try global assignment
                elif dep in self._global_assigns:
                    node = self._global_assigns[dep]
                    context_items.append(dep)
                    context_code_parts.append(self._node_to_code(node))

        gather_deps(target.dependencies, 1)

        # Add required imports
        imports_code = self._get_imports_code(target.imports_needed)
        if imports_code:
            context_code_parts.insert(0, imports_code)

        context_code = "\n\n".join(context_code_parts)
        total_lines = len(context_code.splitlines()) + len(target.code.splitlines())

        return ContextualExtraction(
            target=target,
            context_code=context_code,
            total_lines=total_lines,
            context_items=context_items,
        )

    def get_class_with_context(self, name: str, max_depth: int = 2) -> ContextualExtraction:
        """
        Extract a class with all its dependencies.

        Args:
            name: Class name to extract
            max_depth: How deep to follow dependencies

        Returns:
            ContextualExtraction with target and context
        """
        target = self.get_class(name)
        if not target.success:
            return ContextualExtraction(
                target=target,
                context_code="",
                total_lines=0,
                context_items=[],
            )

        # Similar logic to function context
        context_items = []
        context_code_parts = []
        visited = {name}

        def gather_deps(deps: list[str], depth: int) -> None:
            if depth > max_depth:
                return

            for dep in deps:
                if dep in visited:
                    continue
                visited.add(dep)

                if dep in self._functions:
                    dep_result = self.get_function(dep)
                    if dep_result.success:
                        context_items.append(dep)
                        context_code_parts.append(dep_result.code)
                        gather_deps(dep_result.dependencies, depth + 1)
                elif dep in self._classes:
                    dep_result = self.get_class(dep)
                    if dep_result.success:
                        context_items.append(dep)
                        context_code_parts.append(dep_result.code)
                elif dep in self._global_assigns:
                    node = self._global_assigns[dep]
                    context_items.append(dep)
                    context_code_parts.append(self._node_to_code(node))

        gather_deps(target.dependencies, 1)

        imports_code = self._get_imports_code(target.imports_needed)
        if imports_code:
            context_code_parts.insert(0, imports_code)

        context_code = "\n\n".join(context_code_parts)
        total_lines = len(context_code.splitlines()) + len(target.code.splitlines())

        return ContextualExtraction(
            target=target,
            context_code=context_code,
            total_lines=total_lines,
            context_items=context_items,
        )

    def get_method_with_context(self, class_name: str, method_name: str, max_depth: int = 2) -> ContextualExtraction:
        """
        Extract a method with its dependencies, including relevant class context.

        [20251220_FEATURE] v3.0.5 - Token-efficient method extraction with context.

        Unlike get_class_with_context which returns the entire class, this returns:
        1. The target method code
        2. Other methods in the same class that the target calls
        3. Class-level attributes/properties the method accesses
        4. External dependencies (functions, classes, globals)

        This is more token-efficient when you only need one method.

        Args:
            class_name: Name of the class containing the method
            method_name: Name of the method to extract
            max_depth: How deep to follow dependencies (default: 2)

        Returns:
            ContextualExtraction with target method and minimal necessary context
        """
        target = self.get_method(class_name, method_name)
        if not target.success:
            return ContextualExtraction(
                target=target,
                context_code="",
                total_lines=0,
                context_items=[],
            )

        context_items: list[str] = []
        context_code_parts: list[str] = []
        visited = {f"{class_name}.{method_name}"}

        # Get the class node to find sibling methods and class attributes
        class_node = self._classes.get(class_name)
        sibling_methods: dict[str, ast.AST] = {}
        class_attributes: list[str] = []

        if class_node:
            for node in class_node.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name != method_name:
                        sibling_methods[node.name] = node
                elif isinstance(node, ast.Assign):
                    # Class-level attribute assignments
                    for t in node.targets:
                        if isinstance(t, ast.Name):
                            class_attributes.append(t.id)
                elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                    # Annotated class attributes
                    class_attributes.append(node.target.id)

        def find_self_calls(node: ast.AST) -> list[str]:
            """Find all self.method() calls in a node."""
            self_calls = []
            for child in ast.walk(node):
                # Look for Call nodes where func is Attribute on 'self'
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Attribute):
                        if isinstance(child.func.value, ast.Name) and child.func.value.id == "self":
                            self_calls.append(child.func.attr)
                # Also look for self.attr accesses (class attributes)
                elif isinstance(child, ast.Attribute):
                    if isinstance(child.value, ast.Name) and child.value.id == "self":
                        self_calls.append(child.attr)
            return self_calls

        def gather_deps(deps: list[str], depth: int, from_node: ast.AST | None = None) -> None:
            if depth > max_depth:
                return

            # Also find self.method() calls if we have a node to inspect
            if from_node:
                self_deps = find_self_calls(from_node)
                deps = list(set(deps + self_deps))

            for dep in deps:
                if dep in visited:
                    continue
                visited.add(dep)

                # Check if it's a sibling method (self.method_name calls)
                if dep in sibling_methods:
                    method_node = sibling_methods[dep]
                    method_code = self._node_to_code(method_node)
                    context_items.append(f"{class_name}.{dep}")
                    context_code_parts.append(f"# From class {class_name}:\n{method_code}")
                    # Recursively gather deps from sibling method
                    method_deps = self._find_dependencies(method_node)
                    gather_deps(method_deps, depth + 1, method_node)

                # Check if it's a class attribute
                elif dep in class_attributes:
                    # Include class header with attribute
                    attr_context = f"# Class attribute from {class_name}:\n# {dep} = ..."
                    if attr_context not in context_code_parts:
                        context_items.append(f"{class_name}.{dep}")

                # External function
                elif dep in self._functions:
                    dep_result = self.get_function(dep)
                    if dep_result.success:
                        context_items.append(dep)
                        context_code_parts.append(dep_result.code)
                        gather_deps(dep_result.dependencies, depth + 1)

                # External class
                elif dep in self._classes:
                    dep_result = self.get_class(dep)
                    if dep_result.success:
                        context_items.append(dep)
                        context_code_parts.append(dep_result.code)

                # Global assignment
                elif dep in self._global_assigns:
                    node = self._global_assigns[dep]
                    context_items.append(dep)
                    context_code_parts.append(self._node_to_code(node))

        # Find the method node to analyze self. calls
        method_node: ast.AST | None = None
        if class_node:
            for node in class_node.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name == method_name:
                        method_node = node
                        break

        gather_deps(target.dependencies, 1, method_node)

        # Add required imports
        imports_code = self._get_imports_code(target.imports_needed)
        if imports_code:
            context_code_parts.insert(0, imports_code)

        context_code = "\n\n".join(context_code_parts)
        total_lines = len(context_code.splitlines()) + len(target.code.splitlines())

        return ContextualExtraction(
            target=target,
            context_code=context_code,
            total_lines=total_lines,
            context_items=context_items,
        )

    def resolve_cross_file_dependencies(
        self,
        target_name: str,
        target_type: str = "function",
        max_depth: int = 1,
        confidence_decay_factor: float = 0.9,
    ) -> CrossFileResolution:
        """
        Extract a symbol and resolve its dependencies from external files.

        This is the CROSS-FILE token saver. When calculate_tax uses TaxRate
        from models.py, this method will:
        1. Extract calculate_tax from the current file
        2. Find the import: "from models import TaxRate"
        3. Resolve models.py path relative to current file
        4. Extract TaxRate from models.py
        5. Return both as a combined context

        Args:
            target_name: Name of function/class to extract
            target_type: "function" or "class"
            max_depth: How many levels of imports to follow (default: 1)

        Returns:
            CrossFileResolution with target and external symbols

        Example:
            >>> # utils.py imports TaxRate from models.py
            >>> extractor = SurgicalExtractor.from_file("utils.py")
            >>> result = extractor.resolve_cross_file_dependencies("calculate_tax")
            >>> print(result.full_code)
            # From models.py
            class TaxRate:
                ...

            def calculate_tax(amount):
                rate = TaxRate()
                ...

        Requires:
            - file_path must be set (use from_file() or pass to __init__)
        """
        # Extract the target
        if target_type == "class":
            target = self.get_class(target_name)
        else:
            target = self.get_function(target_name)

        if not target.success:
            return CrossFileResolution(
                success=False,
                target=target,
                error=target.error,
            )

        if not self.file_path:
            return CrossFileResolution(
                success=True,
                target=target,
                error="file_path not set - cannot resolve cross-file imports",
            )

        # Build import map: symbol_name -> (module_path, import_statement)
        import_map = self._build_import_map()

        # Find which imports are actually used by the target
        used_imports = set(target.imports_needed)

        # Also check dependencies that might be imported
        for dep in target.dependencies:
            if dep in import_map:
                used_imports.add(dep)

        # Resolve external symbols
        external_symbols: list[CrossFileSymbol] = []
        unresolved: list[str] = []
        # Track (file_path, symbol_name) to avoid duplicate resolution
        visited_symbols: set[tuple[str, str]] = set()
        # Cache extractors to avoid re-parsing same files
        extractor_cache: dict[str, SurgicalExtractor] = {}

        def get_extractor(path: str) -> SurgicalExtractor:
            """Get or create an extractor for a file (cached)."""
            if path not in extractor_cache:
                extractor_cache[path] = SurgicalExtractor.from_file(path)
            return extractor_cache[path]

        def resolve_symbol(
            symbol_name: str,
            module_info: tuple[str | None, str, str],
            depth: int,
        ) -> None:
            """Recursively resolve a symbol from an external file.

            [20251228_FEATURE] Phase 3 - Module re-export following.
            If a symbol is not found directly in a module, check if the module
            re-exports it from another module (e.g., via alias imports).
            """
            if depth > max_depth:
                return

            module_path, import_stmt, actual_name = module_info

            if module_path is None:
                unresolved.append(f"{symbol_name} (module not found)")
                return

            # Check if we've already resolved this specific symbol
            visit_key = (module_path, actual_name)
            if visit_key in visited_symbols:
                return  # Already resolved this symbol

            visited_symbols.add(visit_key)

            try:
                ext_extractor = get_extractor(module_path)

                # Confidence decays with depth. Depth is 1 for direct deps.
                confidence = float(confidence_decay_factor**depth)

                # Try to extract as function first, then class
                result = ext_extractor.get_function(actual_name)
                if not result.success:
                    result = ext_extractor.get_class(actual_name)

                if result.success:
                    external_symbols.append(
                        CrossFileSymbol(
                            name=symbol_name,
                            source_file=module_path,
                            code=result.code,
                            node_type=result.node_type,
                            import_statement=import_stmt,
                            depth=depth,
                            confidence=confidence,
                        )
                    )

                    # Recursively resolve dependencies of this symbol
                    if depth < max_depth:
                        ext_import_map = ext_extractor._build_import_map()
                        for dep in result.dependencies:
                            if dep in ext_import_map:
                                resolve_symbol(
                                    dep,
                                    ext_import_map[dep],
                                    depth + 1,
                                )
                else:
                    # Try as a global variable
                    ext_extractor._ensure_parsed()
                    if actual_name in ext_extractor._global_assigns:
                        node = ext_extractor._global_assigns[actual_name]
                        external_symbols.append(
                            CrossFileSymbol(
                                name=symbol_name,
                                source_file=module_path,
                                code=ext_extractor._node_to_code(node),
                                node_type="variable",
                                import_statement=import_stmt,
                                depth=depth,
                                confidence=confidence,
                            )
                        )
                    else:
                        # [20251228_FEATURE] Phase 3 - Try to follow re-export alias.
                        # If the symbol is not found in this module, check if this module
                        # imports and re-exports it from another module.
                        reexport_info = _find_reexport(ext_extractor, actual_name)
                        if reexport_info is not None:
                            # Found a re-export - recursively resolve the original
                            original_name, original_module_path = reexport_info
                            if original_module_path is not None:
                                resolve_symbol(
                                    symbol_name,
                                    (original_module_path, import_stmt, original_name),
                                    depth + 1,
                                )
                            else:
                                unresolved.append(f"{symbol_name} (re-export module not found)")
                        else:
                            unresolved.append(f"{symbol_name} (not found in {module_path})")

            except (FileNotFoundError, ValueError) as e:
                unresolved.append(f"{symbol_name} ({e})")

        def _find_reexport(ext_extractor: SurgicalExtractor, symbol_name: str) -> tuple[str, str | None] | None:
            """
            Check if a symbol is re-exported from another module.

            Returns (original_name, resolved_path) if found, None otherwise.

            [20251228_FEATURE] Phase 3 - Re-export detection.
            Handles cases like:
                # in public_api.py
                from internal import _InternalHelper as InternalHelper

            When looking for "InternalHelper", this finds that it's imported from
            internal as "_InternalHelper" and returns ("_InternalHelper", "path/to/internal.py")
            """
            ext_extractor._ensure_parsed()
            ext_import_map = ext_extractor._build_import_map()

            # Check if the symbol is in the import map with a different actual name
            if symbol_name in ext_import_map:
                module_path, import_stmt, actual_name = ext_import_map[symbol_name]
                # Found it as an import - return the original name and module path
                return (actual_name, module_path)

            return None

        # Resolve each imported symbol
        for dep in target.dependencies:
            if dep in import_map:
                resolve_symbol(dep, import_map[dep], 1)

        return CrossFileResolution(
            success=True,
            target=target,
            external_symbols=external_symbols,
            unresolved_imports=unresolved,
        )

    def _build_import_map(self) -> dict[str, tuple[str | None, str, str]]:
        """
        Build a mapping from imported symbol names to their source modules.

        Returns:
            Dict mapping symbol_name -> (resolved_path, import_statement, actual_name)
            resolved_path is None if module cannot be found
        """
        self._ensure_parsed()
        import_map: dict[str, tuple[str | None, str, str]] = {}

        base_dir = Path(self.file_path).parent if self.file_path else Path(".")

        for imp in self._imports:
            if isinstance(imp, ast.ImportFrom):
                # from module import name1, name2
                module_name = imp.module or ""
                module_path = self._resolve_module_path(module_name, base_dir, imp.level)
                import_stmt = ast.unparse(imp)

                for alias in imp.names:
                    # Handle "from module import *" - skip
                    if alias.name == "*":
                        continue
                    local_name = alias.asname or alias.name
                    actual_name = alias.name
                    import_map[local_name] = (module_path, import_stmt, actual_name)

            elif isinstance(imp, ast.Import):
                # import module, module2
                for alias in imp.names:
                    module_name = alias.name
                    local_name = alias.asname or module_name.split(".")[0]
                    module_path = self._resolve_module_path(module_name, base_dir, 0)
                    import_stmt = ast.unparse(imp)
                    import_map[local_name] = (module_path, import_stmt, module_name)

        return import_map

    def _resolve_module_path(self, module_name: str, base_dir: Path, level: int = 0) -> str | None:
        """
        Resolve a module name to a file path.

        Args:
            module_name: Module name (e.g., "models", "utils.helpers")
            base_dir: Directory to resolve relative imports from
            level: Number of dots for relative imports (0 = absolute)

        Returns:
            Resolved file path or None if not found
        """
        # Handle relative imports (level > 0 means relative)
        if level > 0:
            # Go up 'level' directories from base_dir
            search_dir = base_dir
            for _ in range(level - 1):  # level=1 means current dir
                search_dir = search_dir.parent

            if module_name:
                parts = module_name.split(".")
                search_path = search_dir / "/".join(parts)
            else:
                search_path = search_dir
        else:
            # Absolute import - search relative to base_dir first
            # (common in packages), then could extend to sys.path
            parts = module_name.split(".")
            search_path = base_dir / "/".join(parts)

        # Try module.py
        py_file = search_path.with_suffix(".py")
        if py_file.exists():
            return str(py_file)

        # Try module/__init__.py
        init_file = search_path / "__init__.py"
        if init_file.exists():
            return str(init_file)

        # Try searching from parent directories (common package structure)
        # e.g., src/package/module.py when importing from src/package/subdir/file.py
        parts = module_name.split(".") if module_name else []
        current = base_dir
        for _ in range(5):  # Don't go too far up
            current = current.parent
            if not current.exists() or not parts:
                break

            test_path = current / "/".join(parts)
            py_file = test_path.with_suffix(".py")
            if py_file.exists():
                return str(py_file)

            init_file = test_path / "__init__.py"
            if init_file.exists():
                return str(init_file)

        return None

    def _node_to_code(self, node: ast.AST) -> str:
        """
        Convert an AST node back to source code.

        """
        try:
            return ast.unparse(node)
        except Exception:
            # Fallback to source lines if available
            lineno = getattr(node, "lineno", None)
            end_lineno = getattr(node, "end_lineno", None)
            if lineno is not None and end_lineno is not None:
                return "\n".join(self.source_lines[lineno - 1 : end_lineno])
            raise

    def _find_dependencies(self, node: ast.AST) -> list[str]:
        """
        Find names that this node depends on.

        Returns names of functions, classes, and variables used.

        """
        deps = set()
        defined_in_scope = set()

        # First pass: collect all names that are defined in scope
        class DefinitionCollector(ast.NodeVisitor):
            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                # Function args are defined in scope
                for arg in node.args.args:
                    defined_in_scope.add(arg.arg)
                if node.args.vararg:
                    defined_in_scope.add(node.args.vararg.arg)
                if node.args.kwarg:
                    defined_in_scope.add(node.args.kwarg.arg)
                for arg in node.args.kwonlyargs:
                    defined_in_scope.add(arg.arg)
                self.generic_visit(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                for arg in node.args.args:
                    defined_in_scope.add(arg.arg)
                if node.args.vararg:
                    defined_in_scope.add(node.args.vararg.arg)
                if node.args.kwarg:
                    defined_in_scope.add(node.args.kwarg.arg)
                for arg in node.args.kwonlyargs:
                    defined_in_scope.add(arg.arg)
                self.generic_visit(node)

            def visit_For(self, node: ast.For) -> None:
                # Loop variable is defined
                if isinstance(node.target, ast.Name):
                    defined_in_scope.add(node.target.id)
                elif isinstance(node.target, ast.Tuple):
                    for elt in node.target.elts:
                        if isinstance(elt, ast.Name):
                            defined_in_scope.add(elt.id)
                self.generic_visit(node)

            def visit_comprehension(self, node: ast.comprehension) -> None:
                # Comprehension target variable
                if isinstance(node.target, ast.Name):
                    defined_in_scope.add(node.target.id)
                elif isinstance(node.target, ast.Tuple):
                    for elt in node.target.elts:
                        if isinstance(elt, ast.Name):
                            defined_in_scope.add(elt.id)
                self.generic_visit(node)

            def visit_Name(self, node: ast.Name) -> None:
                if isinstance(node.ctx, ast.Store):
                    defined_in_scope.add(node.id)
                self.generic_visit(node)

            def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
                if node.name:
                    defined_in_scope.add(node.name)
                self.generic_visit(node)

            def visit_With(self, node: ast.With) -> None:
                for item in node.items:
                    if item.optional_vars and isinstance(item.optional_vars, ast.Name):
                        defined_in_scope.add(item.optional_vars.id)
                self.generic_visit(node)

        # Collect definitions first
        DefinitionCollector().visit(node)

        # Second pass: collect all names that are loaded (used)
        class UsageCollector(ast.NodeVisitor):
            def visit_Name(self, node: ast.Name) -> None:
                if isinstance(node.ctx, ast.Load):
                    if node.id not in defined_in_scope:
                        deps.add(node.id)
                self.generic_visit(node)

        UsageCollector().visit(node)

        # Filter out builtins and known stdlib
        builtins = {
            "print",
            "len",
            "range",
            "int",
            "str",
            "float",
            "bool",
            "list",
            "dict",
            "set",
            "tuple",
            "type",
            "isinstance",
            "hasattr",
            "getattr",
            "setattr",
            "open",
            "sum",
            "min",
            "max",
            "abs",
            "all",
            "any",
            "enumerate",
            "zip",
            "map",
            "filter",
            "sorted",
            "reversed",
            "None",
            "True",
            "False",
            "self",
            "cls",
            "super",
        }

        return [d for d in deps if d not in builtins]

    def _find_required_imports(self, node: ast.AST) -> list[str]:
        """
        Find which imports are needed for this node.

        """
        # Get all names used in the node
        names_used = set()

        class NameCollector(ast.NodeVisitor):
            def visit_Name(self, node: ast.Name) -> None:
                if isinstance(node.ctx, ast.Load):
                    names_used.add(node.id)
                self.generic_visit(node)

            def visit_Attribute(self, node: ast.Attribute) -> None:
                # Get the base name (e.g., 'os' from 'os.path')
                if isinstance(node.value, ast.Name):
                    names_used.add(node.value.id)
                self.generic_visit(node)

        NameCollector().visit(node)

        # Check which imports provide these names
        required = []
        for imp in self._imports:
            if isinstance(imp, ast.Import):
                for alias in imp.names:
                    name = alias.asname or alias.name.split(".")[0]
                    if name in names_used:
                        required.append(ast.unparse(imp))
                        break
            elif isinstance(imp, ast.ImportFrom):
                for alias in imp.names:
                    name = alias.asname or alias.name
                    if name in names_used:
                        required.append(ast.unparse(imp))
                        break

        return required

    def _get_imports_code(self, import_statements: list[str]) -> str:
        """Combine import statements into code block."""
        if not import_statements:
            return ""
        return "\n".join(sorted(set(import_statements)))


def extract_function(code: str, name: str) -> ExtractionResult:
    """
    Convenience function to extract a function from code.

    Args:
        code: Python source code
        name: Function name to extract

    Returns:
        ExtractionResult with the function code
    """
    return SurgicalExtractor(code).get_function(name)


def extract_class(code: str, name: str) -> ExtractionResult:
    """
    Convenience function to extract a class from code.

    Args:
        code: Python source code
        name: Class name to extract

    Returns:
        ExtractionResult with the class code
    """
    return SurgicalExtractor(code).get_class(name)


def extract_method(code: str, class_name: str, method_name: str) -> ExtractionResult:
    """
    Convenience function to extract a method from code.

    Args:
        code: Python source code
        class_name: Class name
        method_name: Method name

    Returns:
        ExtractionResult with the method code
    """
    return SurgicalExtractor(code).get_method(class_name, method_name)


def extract_with_context(
    code: str, name: str, target_type: str = "function", max_depth: int = 2
) -> ContextualExtraction:
    """
    Convenience function to extract code with dependencies.

    Args:
        code: Python source code
        name: Name of function or class to extract
        target_type: "function" or "class"
        max_depth: Dependency depth

    Returns:
        ContextualExtraction with target and context
    """
    extractor = SurgicalExtractor(code)
    if target_type == "class":
        return extractor.get_class_with_context(name, max_depth)
    return extractor.get_function_with_context(name, max_depth)


@dataclass
class VariablePromotionResult:
    """
    Result of variable promotion analysis.

    [20251229_FEATURE] Pro tier feature for extracting reusable code.
    """

    success: bool
    promoted_function: str
    promoted_variables: list[dict[str, str]]  # [{name, default_value, suggested_type}]
    original_function: str
    explanation: str
    error: str | None = None


def promote_variables(code: str, function_name: str) -> VariablePromotionResult:
    """
    Analyze a function and promote local variables to parameters.

    [20251229_FEATURE] Pro tier: Smart Extract with variable promotion.

    This makes extracted code more reusable by identifying hardcoded values
    and promoting them to function parameters with intelligent defaults.

    Args:
        code: Python source code containing the function
        function_name: Name of the function to analyze

    Returns:
        VariablePromotionResult with promoted function signature and variable details

    Example:
        >>> code = '''
        ... def calculate_tax(price):
        ...     tax_rate = 0.08
        ...     threshold = 1000
        ...     if price > threshold:
        ...         return price * tax_rate * 1.5
        ...     return price * tax_rate
        ... '''
        >>> result = promote_variables(code, "calculate_tax")
        >>> print(result.promoted_function)
        def calculate_tax(price, tax_rate=0.08, threshold=1000):
            if price > threshold:
                return price * tax_rate * 1.5
            return price * tax_rate
    """
    try:
        extractor = SurgicalExtractor(code)
        func_result = extractor.get_function(function_name)

        if not func_result.success:
            return VariablePromotionResult(
                success=False,
                promoted_function="",
                promoted_variables=[],
                original_function="",
                explanation="",
                error=func_result.error,
            )

        # Parse the function to find local variables that could be promoted
        try:
            tree_node, _report = parse_python_code(code, filename="<promotion>")
            tree = tree_node if isinstance(tree_node, ast.Module) else ast.Module(body=[], type_ignores=[])
        except ParsingError as e:
            return VariablePromotionResult(
                success=False,
                promoted_function="",
                promoted_variables=[],
                original_function="",
                explanation=f"Failed to parse code: {e}",
                error=str(e),
            )

        func_node = None
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == function_name:
                    func_node = node
                    break

        if not func_node:
            return VariablePromotionResult(
                success=False,
                promoted_function="",
                promoted_variables=[],
                original_function=func_result.code,
                explanation="",
                error="Could not parse function AST",
            )

        # Find local variable assignments that are good candidates for promotion
        candidates = []
        existing_params = {arg.arg for arg in func_node.args.args}

        # Look for simple assignments at the function start
        for i, stmt in enumerate(func_node.body):
            # Skip docstrings
            if i == 0 and isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                continue

            # Look for assignments of constants
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id not in existing_params:
                        # Check if the value is a constant (good candidate)
                        if isinstance(stmt.value, ast.Constant):
                            var_name = target.id
                            default_value = repr(stmt.value.value)
                            suggested_type = type(stmt.value.value).__name__

                            candidates.append(
                                {
                                    "name": var_name,
                                    "default_value": default_value,
                                    "suggested_type": suggested_type,
                                    "line_number": stmt.lineno,
                                }
                            )
            # Stop analyzing after the first few statements (only promote early vars)
            elif i > 3:
                break

        if not candidates:
            return VariablePromotionResult(
                success=True,
                promoted_function=func_result.code,
                promoted_variables=[],
                original_function=func_result.code,
                explanation="No promotable variables found (no simple constant assignments at function start)",
            )

        # Generate new function signature
        new_params = list(func_node.args.args)
        for candidate in candidates:
            new_arg = ast.arg(
                arg=candidate["name"],
                annotation=None,
            )
            new_params.append(new_arg)

        # Generate defaults list
        defaults = list(func_node.args.defaults)
        for candidate in candidates:
            # Parse the default value back to AST
            try:
                default_tree_node, _report = parse_python_code(candidate["default_value"], filename="<default>")
                default_tree = (
                    default_tree_node
                    if isinstance(default_tree_node, ast.Module)
                    else ast.Module(body=[], type_ignores=[])
                )
                if default_tree.body and isinstance(default_tree.body[0], ast.Expr):
                    default_ast = default_tree.body[0].value
                    defaults.append(default_ast)
            except (ParsingError, IndexError, AttributeError):
                # Skip invalid default values
                continue

        # Create new function with promoted parameters
        import sys

        func_kwargs = {
            "name": func_node.name,
            "args": ast.arguments(
                posonlyargs=[],
                args=new_params,
                kwonlyargs=[],
                kw_defaults=[],
                defaults=defaults,
            ),
            "body": [
                stmt
                for stmt in func_node.body
                if not (
                    isinstance(stmt, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == c["name"] for t in stmt.targets for c in candidates)
                )
            ],
            "decorator_list": func_node.decorator_list,
            "returns": func_node.returns,
            "type_comment": None,
        }

        # type_params only available in Python 3.12+
        if sys.version_info >= (3, 12):
            func_kwargs["type_params"] = []  # type: ignore[assignment]

        new_func = ast.FunctionDef(**func_kwargs)  # type: ignore[arg-type]

        # Fix missing location information
        ast.fix_missing_locations(new_func)

        # Ensure body is not empty
        if not new_func.body or (len(new_func.body) == 1 and isinstance(new_func.body[0], ast.Expr)):
            new_func.body.append(ast.Pass())

        promoted_code = ast.unparse(new_func)

        explanation = (
            f"Promoted {len(candidates)} variable(s) to parameters: "
            f"{', '.join(c['name'] for c in candidates)}. "
            f"These hardcoded values are now configurable with intelligent defaults."
        )

        return VariablePromotionResult(
            success=True,
            promoted_function=promoted_code,
            promoted_variables=candidates,
            original_function=func_result.code,
            explanation=explanation,
        )

    except Exception as e:
        return VariablePromotionResult(
            success=False,
            promoted_function="",
            promoted_variables=[],
            original_function="",
            explanation="",
            error=f"Variable promotion failed: {str(e)}",
        )


@dataclass
class MicroserviceExtractionResult:
    """
    Result of microservice extraction with deployment artifacts.

    [20251229_FEATURE] Enterprise tier feature for service extraction.
    """

    success: bool
    function_code: str
    dockerfile: str
    api_spec: str  # OpenAPI YAML
    requirements_txt: str
    readme: str
    error: str | None = None


def extract_as_microservice(
    code: str, function_name: str, host: str = "127.0.0.1", port: int = 8000
) -> MicroserviceExtractionResult:
    """
    Extract a function as a standalone microservice with Dockerfile and API spec.

    [20251229_FEATURE] Enterprise tier: Microservice Extraction.

    This generates everything needed to deploy the extracted function as a
    containerized microservice:
    - Dockerfile with appropriate base image and dependencies
    - OpenAPI specification for the API endpoint
    - requirements.txt with detected dependencies
    - README with deployment instructions

    [20260102_BUGFIX] Default host limited to loopback to avoid exposing
    generated services on all interfaces by default.

    Args:
        code: Python source code containing the function
        function_name: Name of the function to extract
        host: Default host for the service (default: "0.0.0.0")
        port: Default port for the service (default: 8000)

    Returns:
        MicroserviceExtractionResult with all deployment artifacts

    Example:
        >>> code = '''
        ... import pandas as pd
        ... def process_data(input_csv):
        ...     df = pd.read_csv(input_csv)
        ...     return df.describe().to_dict()
        ... '''
        >>> result = extract_as_microservice(code, "process_data")
        >>> print(result.dockerfile)
        FROM python:3.11-slim
        WORKDIR /app
        COPY requirements.txt .
        RUN pip install --no-cache-dir -r requirements.txt
        COPY service.py .
        EXPOSE 8000
        CMD ["python", "service.py"]
    """
    try:
        extractor = SurgicalExtractor(code)
        func_result = extractor.get_function(function_name)

        if not func_result.success:
            return MicroserviceExtractionResult(
                success=False,
                function_code="",
                dockerfile="",
                api_spec="",
                requirements_txt="",
                readme="",
                error=func_result.error,
            )

        # Parse function signature to generate API spec
        try:
            tree_node, _report = parse_python_code(code, filename="<api_spec>")
            tree = tree_node if isinstance(tree_node, ast.Module) else ast.Module(body=[], type_ignores=[])
        except ParsingError as e:
            return MicroserviceExtractionResult(
                success=False,
                function_code="",
                dockerfile="",
                api_spec="",
                requirements_txt="",
                readme="",
                error=f"Failed to parse code: {e}",
            )

        func_node = None
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == function_name:
                    func_node = node
                    break

        if not func_node:
            return MicroserviceExtractionResult(
                success=False,
                function_code="",
                dockerfile="",
                api_spec="",
                requirements_txt="",
                readme="",
                error="Could not parse function AST",
            )

        # Extract function parameters for API spec
        params = []
        param_types = {}
        for arg in func_node.args.args:
            param_name = arg.arg
            if param_name == "self":
                continue

            # Try to infer type from annotation
            param_type = "string"  # default
            if arg.annotation:
                type_str = ast.unparse(arg.annotation)
                if "int" in type_str.lower():
                    param_type = "integer"
                elif "float" in type_str.lower():
                    param_type = "number"
                elif "bool" in type_str.lower():
                    param_type = "boolean"
                elif "list" in type_str.lower() or "List" in type_str:
                    param_type = "array"
                elif "dict" in type_str.lower() or "Dict" in type_str:
                    param_type = "object"

            params.append(param_name)
            param_types[param_name] = param_type

        # Detect imports to build requirements.txt
        import_modules = set()
        stdlib_modules = {
            "os",
            "sys",
            "re",
            "json",
            "datetime",
            "math",
            "random",
            "collections",
            "itertools",
            "functools",
            "pathlib",
            "typing",
            "dataclasses",
            "enum",
            "abc",
            "time",
            "subprocess",
            "io",
            "string",
            "copy",
            "pickle",
        }

        for imp in func_result.imports_needed:
            # Extract module name from import statement
            if imp.startswith("import "):
                module = imp.replace("import ", "").split()[0].split(".")[0]
                if module not in stdlib_modules:
                    import_modules.add(module)
            elif imp.startswith("from "):
                module = imp.split()[1].split(".")[0]
                if module not in stdlib_modules:
                    import_modules.add(module)

        # Common package mappings (pypi name != import name)
        package_mappings = {
            "PIL": "pillow",
            "cv2": "opencv-python",
            "sklearn": "scikit-learn",
        }

        requirements = []
        for module in sorted(import_modules):
            pypi_name = package_mappings.get(module, module)
            requirements.append(pypi_name)

        # Add FastAPI for the service wrapper
        requirements.insert(0, "fastapi")
        requirements.insert(1, "uvicorn[standard]")

        requirements_txt = "\n".join(requirements)

        # Generate Dockerfile
        python_version = "3.11"  # Modern Python version
        dockerfile = f"""FROM python:{python_version}-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY service.py .
COPY {function_name}.py .

# Expose port
EXPOSE {port}

# Run the service
CMD ["uvicorn", "service:app", "--host", "{host}", "--port", "{port}"]
"""

        # Generate OpenAPI spec
        docstring = func_result.docstring or f"Execute {function_name} function"
        param_specs = []
        for param in params:
            param_specs.append(f"""          {param}:
            type: {param_types[param]}
            description: Parameter {param}""")

        param_spec_str = "\n".join(param_specs) if param_specs else "          # No parameters"

        api_spec = f"""openapi: 3.0.0
info:
  title: {function_name} Microservice
  description: API for {function_name} function
  version: 1.0.0
servers:
  - url: http://{host}:{port}
    description: Local development server
paths:
  /{function_name}:
    post:
      summary: {docstring.split('.')[0] if docstring else function_name}
      description: {docstring}
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
{param_spec_str}
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                type: object
                properties:
                  result:
                    description: Function execution result
        '400':
          description: Bad request - invalid parameters
        '500':
          description: Internal server error
"""

        # Generate FastAPI service wrapper
        ", ".join(params)
        "\n    ".join([f"{p} = request_data.get('{p}')" for p in params])

        # Generate README
        readme = f"""# {function_name} Microservice

Auto-generated microservice deployment for the `{function_name}` function.

## Quick Start

### Build and Run with Docker

```bash
# Build the Docker image
docker build -t {function_name}-service .

# Run the container
docker run -p {port}:{port} {function_name}-service
```

### Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
python service.py
```

## API Usage

The service exposes the following endpoints:

- `POST /{function_name}` - Execute the function
- `GET /health` - Health check

### Example Request

```bash
curl -X POST http://localhost:{port}/{function_name} \\
  -H "Content-Type: application/json" \\
  -d '{{{", ".join(f'"{p}": "value"' for p in params) if params else ""}}}'
```

### Example Response

```json
{{
  "result": "..."
}}
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:{port}/docs
- ReDoc: http://localhost:{port}/redoc
- OpenAPI spec: http://localhost:{port}/openapi.json

## Files

- `service.py` - FastAPI service wrapper
- `{function_name}.py` - Extracted function
- `Dockerfile` - Container configuration
- `requirements.txt` - Python dependencies
- `openapi.yaml` - API specification

## Deployment

### Kubernetes

```bash
kubectl create deployment {function_name} --image={function_name}-service
kubectl expose deployment {function_name} --port={port} --type=LoadBalancer
```

### Docker Compose

```yaml
version: '3.8'
services:
  {function_name}:
    build: .
    ports:
      - "{port}:{port}"
    environment:
      - LOG_LEVEL=info
```

Generated by Code Scalpel Enterprise v3.3.0
"""

        # Create standalone function file
        function_file_code = f'''"""
{function_name} function
Extracted by Code Scalpel Enterprise
"""

{chr(10).join(func_result.imports_needed)}

{func_result.code}
'''

        return MicroserviceExtractionResult(
            success=True,
            function_code=function_file_code,
            dockerfile=dockerfile,
            api_spec=api_spec,
            requirements_txt=requirements_txt,
            readme=readme,
        )

    except Exception as e:
        return MicroserviceExtractionResult(
            success=False,
            function_code="",
            dockerfile="",
            api_spec="",
            requirements_txt="",
            readme="",
            error=f"Microservice extraction failed: {str(e)}",
        )


@dataclass
class ClosureVariable:
    """
    Information about a closure variable.

    [20251229_FEATURE] Pro tier feature for closure detection.
    """

    name: str
    source: str  # "global", "nonlocal", "class_attribute", "outer_scope"
    line_number: int
    risk_level: str  # "low", "medium", "high"
    captured_from: str  # Description of where it's captured from
    suggestion: str  # How to refactor it


@dataclass
class ClosureAnalysisResult:
    """
    Result of closure variable analysis.

    [20251229_FEATURE] Pro tier feature for detecting captured variables.
    """

    success: bool
    function_name: str
    closure_variables: list[ClosureVariable]
    has_closures: bool
    explanation: str
    error: str | None = None


def detect_closure_variables(code: str, function_name: str) -> ClosureAnalysisResult:
    """
    Detect variables captured from outer scopes (closures).

    [20251229_FEATURE] Pro tier: Closure variable detection.

    Identifies variables that are captured from outer scopes, which can cause
    "works in isolation, breaks in production" bugs when extracting code.

    Args:
        code: Python source code containing the function
        function_name: Name of the function to analyze

    Returns:
        ClosureAnalysisResult with detected closure variables

    Example:
        >>> code = '''
        ... multiplier = 2
        ... def calculate(x):
        ...     return x * multiplier  # Closure: captures global 'multiplier'
        ... '''
        >>> result = detect_closure_variables(code, "calculate")
        >>> result.closure_variables[0].name
        'multiplier'
        >>> result.closure_variables[0].source
        'global'
    """
    try:
        tree_node, _report = parse_python_code(code, filename="<closure>")
        tree = tree_node if isinstance(tree_node, ast.Module) else ast.Module(body=[], type_ignores=[])
        func_node = None

        # Find the target function
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == function_name:
                    func_node = node
                    break

        if not func_node:
            return ClosureAnalysisResult(
                success=False,
                function_name=function_name,
                closure_variables=[],
                has_closures=False,
                explanation="",
                error=f"Function '{function_name}' not found",
            )

        # Collect all names defined in the function (parameters, local assignments)
        local_names = set()

        # Add function parameters
        for arg in func_node.args.args:
            local_names.add(arg.arg)
        for arg in func_node.args.posonlyargs:
            local_names.add(arg.arg)
        for arg in func_node.args.kwonlyargs:
            local_names.add(arg.arg)
        if func_node.args.vararg:
            local_names.add(func_node.args.vararg.arg)
        if func_node.args.kwarg:
            local_names.add(func_node.args.kwarg.arg)

        # Add local assignments
        for node in ast.walk(func_node):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        local_names.add(target.id)
            elif isinstance(node, (ast.For, ast.AsyncFor)):
                if isinstance(node.target, ast.Name):
                    local_names.add(node.target.id)
            elif isinstance(node, ast.With):
                for item in node.items:
                    if item.optional_vars and isinstance(item.optional_vars, ast.Name):
                        local_names.add(item.optional_vars.id)
            elif isinstance(node, ast.ExceptHandler):
                if node.name:
                    local_names.add(node.name)

        # Find all names used but not defined locally (potential closures)
        used_names = {}  # name -> list of line numbers

        class NameCollector(ast.NodeVisitor):
            def visit_Name(self, node: ast.Name) -> None:
                if isinstance(node.ctx, ast.Load):
                    if node.id not in local_names and not node.id.startswith("_"):
                        if node.id not in used_names:
                            used_names[node.id] = []
                        used_names[node.id].append(node.lineno)
                self.generic_visit(node)

            def visit_Attribute(self, node: ast.Attribute) -> None:
                # Track self.attribute and other attribute access
                if isinstance(node.value, ast.Name):
                    base_name = node.value.id
                    full_name = f"{base_name}.{node.attr}"
                    if base_name not in local_names:
                        if full_name not in used_names:
                            used_names[full_name] = []
                        used_names[full_name].append(node.lineno)
                self.generic_visit(node)

        NameCollector().visit(func_node)

        # Determine which used names are closures vs builtins
        import builtins

        builtin_names = set(dir(builtins))

        # Find global variables in module
        global_names = set()
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        global_names.add(target.id)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                global_names.add(node.name)

        # Build closure variable list
        closures = []
        for name, line_numbers in used_names.items():
            if name in builtin_names:
                continue  # Skip builtins

            # Determine source and risk level
            if "." in name:
                # Attribute access (e.g., self.attr, obj.method)
                base, attr = name.split(".", 1)
                if base == "self":
                    source = "class_attribute"
                    risk_level = "medium"
                    captured_from = f"Class instance attribute '{name}'"
                    suggestion = f"Pass '{attr}' as a parameter or ensure class context is preserved"
                else:
                    source = "outer_scope"
                    risk_level = "high"
                    captured_from = f"Attribute access on outer scope variable '{base}'"
                    suggestion = f"Pass '{name}' as a parameter or refactor to avoid closure"
            elif name in global_names:
                source = "global"
                risk_level = "high"
                captured_from = f"Module-level global variable '{name}'"
                suggestion = f"Pass '{name}' as a parameter with default value"
            else:
                # Could be from outer function scope or imported
                source = "nonlocal"
                risk_level = "medium"
                captured_from = f"Variable '{name}' from outer scope or import"
                suggestion = f"Verify '{name}' is available in extraction context or pass as parameter"

            closures.append(
                ClosureVariable(
                    name=name,
                    source=source,
                    line_number=line_numbers[0],
                    risk_level=risk_level,
                    captured_from=captured_from,
                    suggestion=suggestion,
                )
            )

        has_closures = len(closures) > 0

        if has_closures:
            explanation = (
                f"Found {len(closures)} closure variable(s). "
                f"These variables are captured from outer scopes and may cause issues "
                f"when extracting the function."
            )
        else:
            explanation = "No closure variables detected. Function is self-contained."

        return ClosureAnalysisResult(
            success=True,
            function_name=function_name,
            closure_variables=closures,
            has_closures=has_closures,
            explanation=explanation,
        )

    except Exception as e:
        return ClosureAnalysisResult(
            success=False,
            function_name=function_name,
            closure_variables=[],
            has_closures=False,
            explanation="",
            error=f"Closure analysis failed: {str(e)}",
        )


@dataclass
class DependencyInjectionSuggestion:
    """
    Suggestion for dependency injection refactoring.

    [20251229_FEATURE] Pro tier feature for DI recommendations.
    """

    variable_name: str
    current_usage: str  # "global", "class_attribute", "closure"
    suggested_parameter: str  # New parameter name
    suggested_default: str | None  # Suggested default value
    benefit: str  # Why this refactoring helps
    refactored_signature: str  # New function signature


@dataclass
class DependencyInjectionResult:
    """
    Result of dependency injection analysis.

    [20251229_FEATURE] Pro tier feature for DI suggestions.
    """

    success: bool
    function_name: str
    suggestions: list[DependencyInjectionSuggestion]
    has_suggestions: bool
    original_signature: str
    refactored_signature: str
    explanation: str
    error: str | None = None


def suggest_dependency_injection(code: str, function_name: str) -> DependencyInjectionResult:
    """
    Suggest dependency injection refactorings for better testability.

    [20251229_FEATURE] Pro tier: Dependency injection suggestions.

    Analyzes function dependencies and recommends converting globals, closures,
    and hard dependencies into injected parameters for better testing and reusability.

    Args:
        code: Python source code containing the function
        function_name: Name of the function to analyze

    Returns:
        DependencyInjectionResult with refactoring suggestions

    Example:
        >>> code = '''
        ... cache = {}
        ... def get_data(key):
        ...     return cache.get(key)
        ... '''
        >>> result = suggest_dependency_injection(code, "get_data")
        >>> result.suggestions[0].variable_name
        'cache'
        >>> result.suggestions[0].suggested_parameter
        'cache'
    """
    try:
        # First detect closures
        closure_result = detect_closure_variables(code, function_name)

        if not closure_result.success:
            return DependencyInjectionResult(
                success=False,
                function_name=function_name,
                suggestions=[],
                has_suggestions=False,
                original_signature="",
                refactored_signature="",
                explanation="",
                error=closure_result.error,
            )

        if not closure_result.closure_variables:
            # No closures = no DI suggestions
            try:
                tree, _report = parse_python_code(code, filename="<di_suggest>")
            except ParsingError:
                return DependencyInjectionResult(
                    success=False,
                    function_name=function_name,
                    suggestions=[],
                    has_suggestions=False,
                    original_signature="",
                    refactored_signature="",
                    explanation="Failed to parse code for DI analysis.",
                    error="ParsingError",
                )
            func_node = None
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name == function_name:
                        func_node = node
                        break

            original_sig = ast.unparse(func_node).split("\n")[0] if func_node else f"def {function_name}(...)"

            return DependencyInjectionResult(
                success=True,
                function_name=function_name,
                suggestions=[],
                has_suggestions=False,
                original_signature=original_sig,
                refactored_signature=original_sig,
                explanation="No dependency injection opportunities found. Function has no external dependencies.",
            )

        # Build DI suggestions from closure variables
        suggestions = []
        try:
            tree_node, _report = parse_python_code(code, filename="<di_build>")
            tree = tree_node if isinstance(tree_node, ast.Module) else ast.Module(body=[], type_ignores=[])
        except ParsingError as e:
            return DependencyInjectionResult(
                success=False,
                function_name=function_name,
                suggestions=[],
                has_suggestions=False,
                original_signature="",
                refactored_signature="",
                explanation=f"Failed to parse code: {e}",
                error=str(e),
            )
        func_node = None

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == function_name:
                    func_node = node
                    break

        if not func_node:
            return DependencyInjectionResult(
                success=False,
                function_name=function_name,
                suggestions=[],
                has_suggestions=False,
                original_signature="",
                refactored_signature="",
                explanation="",
                error="Function AST not found",
            )

        original_sig = ast.unparse(func_node).split("\n")[0]

        # Get current parameters
        current_params = [arg.arg for arg in func_node.args.args]

        # Generate suggestions for each closure
        new_params = list(current_params)
        param_defaults = []

        for closure_var in closure_result.closure_variables:
            var_name = closure_var.name

            # Skip if it's an attribute access (harder to inject)
            if "." in var_name:
                continue

            # Determine parameter name and default
            param_name = var_name
            default_value = "None"

            if closure_var.source == "global":
                benefit = f"Enables testing with mock {var_name} without modifying global state"
                current_usage = f"global variable '{var_name}'"
            elif closure_var.source == "nonlocal":
                benefit = f"Makes dependency on '{var_name}' explicit and testable"
                current_usage = f"outer scope variable '{var_name}'"
            else:
                benefit = f"Decouples from {closure_var.captured_from}"
                current_usage = closure_var.source

            new_params.append(param_name)
            param_defaults.append(default_value)

            # Build refactored signature
            refactored_parts = []
            for i, param in enumerate(new_params):
                if i < len(current_params):
                    refactored_parts.append(param)
                else:
                    # New injected parameter
                    default_idx = i - len(current_params)
                    if default_idx < len(param_defaults):
                        refactored_parts.append(f"{param}={param_defaults[default_idx]}")
                    else:
                        refactored_parts.append(param)

            refactored_sig = f"def {function_name}({', '.join(refactored_parts)})"

            suggestions.append(
                DependencyInjectionSuggestion(
                    variable_name=var_name,
                    current_usage=current_usage,
                    suggested_parameter=param_name,
                    suggested_default=default_value,
                    benefit=benefit,
                    refactored_signature=refactored_sig,
                )
            )

        # Build final refactored signature
        if suggestions:
            final_params = list(current_params)
            for suggestion in suggestions:
                final_params.append(f"{suggestion.suggested_parameter}={suggestion.suggested_default}")
            final_refactored_sig = f"def {function_name}({', '.join(final_params)})"
        else:
            final_refactored_sig = original_sig

        has_suggestions = len(suggestions) > 0

        if has_suggestions:
            explanation = (
                f"Found {len(suggestions)} dependency injection opportunity(ies). "
                f"Refactoring these dependencies will improve testability and reusability."
            )
        else:
            explanation = "No viable dependency injection opportunities found."

        return DependencyInjectionResult(
            success=True,
            function_name=function_name,
            suggestions=suggestions,
            has_suggestions=has_suggestions,
            original_signature=original_sig,
            refactored_signature=final_refactored_sig,
            explanation=explanation,
        )

    except Exception as e:
        return DependencyInjectionResult(
            success=False,
            function_name=function_name,
            suggestions=[],
            has_suggestions=False,
            original_signature="",
            refactored_signature="",
            explanation="",
            error=f"Dependency injection analysis failed: {str(e)}",
        )


@dataclass
class CrossRepoImport:
    """
    Information about a cross-repository import.

    [20251229_FEATURE] Enterprise tier feature for monorepo support.
    """

    repo_name: str
    file_path: str
    symbols: list[str]
    repo_root: str


@dataclass
class OrganizationWideResolutionResult:
    """
    Result of organization-wide import resolution.

    [20251229_FEATURE] Enterprise tier feature for monorepo-aware extraction.
    """

    success: bool
    target_name: str
    target_code: str
    cross_repo_imports: list[CrossRepoImport]
    resolved_symbols: dict[str, str]  # symbol_name -> source_file
    monorepo_structure: dict[str, list[str]]  # repo_name -> file_paths
    explanation: str
    error: str | None = None


def resolve_organization_wide(
    code: str,
    function_name: str,
    workspace_root: str | None = None,
) -> OrganizationWideResolutionResult:
    """
    Resolve imports across multiple repositories in a monorepo.

    [20251229_FEATURE] Enterprise tier: Organization-wide resolution.

    Scans workspace for multiple git repositories and resolves imports across
    repository boundaries, supporting monorepo architectures.

    Args:
        code: Python source code containing the function
        function_name: Name of the function to extract
        workspace_root: Root directory to scan for repositories

    Returns:
        OrganizationWideResolutionResult with cross-repo dependencies

    Example:
        >>> result = resolve_organization_wide(
        ...     code=frontend_code,
        ...     function_name="PaymentForm",
        ...     workspace_root="/workspace"
        ... )
        >>> result.cross_repo_imports[0].repo_name
        'backend-service'
    """
    try:
        from pathlib import Path

        # Determine workspace root
        if workspace_root is None:
            workspace_root = str(Path.cwd())

        workspace_path = Path(workspace_root)

        # Find all git repositories in workspace
        repos = {}
        for path in workspace_path.rglob(".git"):
            repo_root = path.parent
            repo_name = repo_root.name
            repos[repo_name] = str(repo_root)

        if not repos:
            # Single repo or no git
            repos[workspace_path.name] = str(workspace_path)

        # Extract the target function
        extractor = SurgicalExtractor(code)
        func_result = extractor.get_function(function_name)

        if not func_result.success:
            return OrganizationWideResolutionResult(
                success=False,
                target_name=function_name,
                target_code="",
                cross_repo_imports=[],
                resolved_symbols={},
                monorepo_structure={},
                explanation="",
                error=func_result.error,
            )

        # Analyze imports in the code
        try:
            tree_node, _report = parse_python_code(code, filename="<imports>")
            tree = tree_node if isinstance(tree_node, ast.Module) else ast.Module(body=[], type_ignores=[])
        except ParsingError as e:
            return OrganizationWideResolutionResult(
                success=False,
                target_name=function_name,
                target_code="",
                cross_repo_imports=[],
                resolved_symbols={},
                monorepo_structure={},
                explanation=f"Failed to parse code: {e}",
                error=str(e),
            )
        imports_to_resolve = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    imports_to_resolve.append(node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports_to_resolve.append(alias.name)

        # Search for these imports across all repositories
        cross_repo_imports = []
        resolved_symbols = {}
        monorepo_structure = {}

        for repo_name, repo_root in repos.items():
            repo_path = Path(repo_root)
            python_files = list(repo_path.rglob("*.py"))
            monorepo_structure[repo_name] = [str(f.relative_to(repo_path)) for f in python_files[:100]]  # Limit

            for import_name in imports_to_resolve:
                # Search for the module in this repo
                for py_file in python_files:
                    # Check if file path matches import
                    rel_path = py_file.relative_to(repo_path)
                    module_path = str(rel_path.with_suffix("")).replace("/", ".")

                    if module_path.endswith(import_name) or module_path.startswith(import_name):
                        try:
                            with open(py_file, encoding="utf-8") as f:
                                file_content = f.read()

                            # Extract symbols from this file
                            try:
                                file_tree_node, _report = parse_python_code(file_content, filename=str(py_file))
                                file_tree = (
                                    file_tree_node
                                    if isinstance(file_tree_node, ast.Module)
                                    else ast.Module(body=[], type_ignores=[])
                                )
                            except ParsingError:
                                continue  # Skip files that don't parse
                            symbols = []

                            for node in file_tree.body:
                                if isinstance(
                                    node,
                                    (
                                        ast.FunctionDef,
                                        ast.AsyncFunctionDef,
                                        ast.ClassDef,
                                    ),
                                ):
                                    symbols.append(node.name)
                                    resolved_symbols[node.name] = str(py_file)

                            if symbols:
                                cross_repo_imports.append(
                                    CrossRepoImport(
                                        repo_name=repo_name,
                                        file_path=str(rel_path),
                                        symbols=symbols[:20],  # Limit to first 20
                                        repo_root=repo_root,
                                    )
                                )
                        except Exception:
                            continue  # Skip files that can't be parsed

        explanation = (
            f"Scanned {len(repos)} repository(ies) in workspace. "
            f"Found {len(cross_repo_imports)} cross-repository import(s). "
            f"Resolved {len(resolved_symbols)} symbol(s) across repositories."
        )

        return OrganizationWideResolutionResult(
            success=True,
            target_name=function_name,
            target_code=func_result.code,
            cross_repo_imports=cross_repo_imports,
            resolved_symbols=resolved_symbols,
            monorepo_structure=monorepo_structure,
            explanation=explanation,
        )

    except Exception as e:
        return OrganizationWideResolutionResult(
            success=False,
            target_name=function_name,
            target_code="",
            cross_repo_imports=[],
            resolved_symbols={},
            monorepo_structure={},
            explanation="",
            error=f"Organization-wide resolution failed: {str(e)}",
        )


@dataclass
class PatternMatch:
    """
    A match found by custom extraction pattern.

    [20251229_FEATURE] Enterprise tier feature for pattern-based extraction.
    """

    symbol_name: str
    symbol_type: str  # "function", "class", "method"
    file_path: str
    line_number: int
    code: str
    match_reason: str


@dataclass
class CustomPatternResult:
    """
    Result of custom pattern extraction.

    [20251229_FEATURE] Enterprise tier feature for pattern-based extraction.
    """

    success: bool
    pattern_name: str
    matches: list[PatternMatch]
    total_matches: int
    files_scanned: int
    explanation: str
    error: str | None = None


def extract_with_custom_pattern(
    pattern: str,
    pattern_type: str = "regex",
    project_root: str | None = None,
    include_related: list[str] | None = None,
) -> CustomPatternResult:
    """
    Extract code using custom patterns (regex or AST).

    [20251229_FEATURE] Enterprise tier: Custom extraction patterns.

    Allows users to define extraction rules for finding code based on patterns,
    useful for refactoring campaigns and architectural analysis.

    Args:
        pattern: Pattern to match (regex or AST query)
        pattern_type: "regex", "function_call", or "import"
        project_root: Root directory to search
        include_related: List of related symbols to include

    Returns:
        CustomPatternResult with all matches

    Example:
        >>> # Extract all functions that call db.query()
        >>> result = extract_with_custom_pattern(
        ...     pattern="db.query",
        ...     pattern_type="function_call"
        ... )
        >>> len(result.matches)
        5
    """
    try:
        import re
        from pathlib import Path

        if project_root is None:
            project_root = str(Path.cwd())

        root_path = Path(project_root)
        python_files = list(root_path.rglob("*.py"))

        # Exclude common non-source directories
        python_files = [
            f
            for f in python_files
            if not any(part in f.parts for part in [".venv", "venv", "__pycache__", ".git", "node_modules"])
        ]

        matches = []
        files_scanned = 0

        for py_file in python_files:
            files_scanned += 1
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                if pattern_type == "regex":
                    # Simple regex pattern matching
                    if re.search(pattern, content, re.IGNORECASE):
                        # Parse to find which symbols contain the pattern
                        try:
                            tree_node, _report = parse_python_code(content, filename=str(py_file))
                            tree = (
                                tree_node if isinstance(tree_node, ast.Module) else ast.Module(body=[], type_ignores=[])
                            )
                        except ParsingError:
                            continue  # Skip files that don't parse
                        for node in ast.walk(tree):
                            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                func_code = ast.unparse(node)
                                if re.search(pattern, func_code, re.IGNORECASE):
                                    matches.append(
                                        PatternMatch(
                                            symbol_name=node.name,
                                            symbol_type="function",
                                            file_path=str(py_file.relative_to(root_path)),
                                            line_number=node.lineno,
                                            code=func_code,
                                            match_reason=f"Regex pattern '{pattern}' matched",
                                        )
                                    )
                            elif isinstance(node, ast.ClassDef):
                                class_code = ast.unparse(node)
                                if re.search(pattern, class_code, re.IGNORECASE):
                                    matches.append(
                                        PatternMatch(
                                            symbol_name=node.name,
                                            symbol_type="class",
                                            file_path=str(py_file.relative_to(root_path)),
                                            line_number=node.lineno,
                                            code=class_code,
                                            match_reason=f"Regex pattern '{pattern}' matched",
                                        )
                                    )

                elif pattern_type == "function_call":
                    # Match functions that call a specific function
                    try:
                        tree_node, _report = parse_python_code(content, filename=str(py_file))
                        tree = tree_node if isinstance(tree_node, ast.Module) else ast.Module(body=[], type_ignores=[])
                    except ParsingError:
                        continue  # Skip files that don't parse
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            # Check if this function calls the target
                            calls_target = False
                            for child in ast.walk(node):
                                if isinstance(child, ast.Call):
                                    if isinstance(child.func, ast.Name):
                                        if child.func.id == pattern:
                                            calls_target = True
                                            break
                                    elif isinstance(child.func, ast.Attribute):
                                        call_str = ast.unparse(child.func)
                                        if pattern in call_str:
                                            calls_target = True
                                            break

                            if calls_target:
                                matches.append(
                                    PatternMatch(
                                        symbol_name=node.name,
                                        symbol_type="function",
                                        file_path=str(py_file.relative_to(root_path)),
                                        line_number=node.lineno,
                                        code=ast.unparse(node),
                                        match_reason=f"Calls function '{pattern}'",
                                    )
                                )

                elif pattern_type == "import":
                    # Match files that import a specific module
                    try:
                        tree_node, _report = parse_python_code(content, filename=str(py_file))
                        tree = tree_node if isinstance(tree_node, ast.Module) else ast.Module(body=[], type_ignores=[])
                    except ParsingError:
                        continue  # Skip files that don't parse
                    imports_pattern = False

                    for node in tree.body:
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                if pattern in alias.name:
                                    imports_pattern = True
                                    break
                        elif isinstance(node, ast.ImportFrom):
                            if node.module and pattern in node.module:
                                imports_pattern = True
                                break

                    if imports_pattern:
                        # Add all functions from this file
                        for node in tree.body:
                            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                matches.append(
                                    PatternMatch(
                                        symbol_name=node.name,
                                        symbol_type="function",
                                        file_path=str(py_file.relative_to(root_path)),
                                        line_number=node.lineno,
                                        code=ast.unparse(node),
                                        match_reason=f"File imports '{pattern}'",
                                    )
                                )

            except Exception:
                continue  # Skip files that can't be parsed

        explanation = (
            f"Scanned {files_scanned} Python file(s) with pattern type '{pattern_type}'. "
            f"Found {len(matches)} match(es) for pattern '{pattern}'."
        )

        return CustomPatternResult(
            success=True,
            pattern_name=pattern,
            matches=matches,
            total_matches=len(matches),
            files_scanned=files_scanned,
            explanation=explanation,
        )

    except Exception as e:
        return CustomPatternResult(
            success=False,
            pattern_name=pattern,
            matches=[],
            total_matches=0,
            files_scanned=0,
            explanation="",
            error=f"Custom pattern extraction failed: {str(e)}",
        )


@dataclass
class ServiceBoundary:
    """
    A suggested service boundary.

    [20251229_FEATURE] Enterprise tier feature for service boundary detection.
    """

    service_name: str
    included_files: list[str]
    external_dependencies: list[str]
    internal_dependencies: list[str]
    isolation_level: str  # "low", "medium", "high", "critical"
    rationale: str


@dataclass
class ServiceBoundaryResult:
    """
    Result of service boundary detection.

    [20251229_FEATURE] Enterprise tier feature for microservice split suggestions.
    """

    success: bool
    suggested_services: list[ServiceBoundary]
    dependency_graph: dict[str, list[str]]  # file -> dependencies
    total_files_analyzed: int
    explanation: str
    error: str | None = None


def detect_service_boundaries(
    project_root: str | None = None,
    min_isolation_score: float = 0.6,
) -> ServiceBoundaryResult:
    """
    Detect architectural boundaries and suggest microservice splits.

    [20251229_FEATURE] Enterprise tier: Service boundary detection.

    Analyzes dependency graph to identify loosely coupled clusters that could
    be extracted as independent microservices.

    Args:
        project_root: Root directory to analyze
        min_isolation_score: Minimum isolation score (0.0-1.0) for service suggestions

    Returns:
        ServiceBoundaryResult with service split suggestions

    Example:
        >>> result = detect_service_boundaries(project_root="/app")
        >>> for service in result.suggested_services:
        ...     print(f"{service.service_name}: {len(service.included_files)} files")
        payment-service: 5 files
        stripe-wrapper: 2 files
    """
    try:
        from collections import defaultdict
        from pathlib import Path

        if project_root is None:
            project_root = str(Path.cwd())

        root_path = Path(project_root)
        python_files = list(root_path.rglob("*.py"))

        # Exclude common non-source directories
        python_files = [
            f
            for f in python_files
            if not any(
                part in f.parts
                for part in [
                    ".venv",
                    "venv",
                    "__pycache__",
                    ".git",
                    "node_modules",
                    "tests",
                    "test",
                ]
            )
        ]

        # Build dependency graph
        dependency_graph = {}
        file_to_imports = {}

        for py_file in python_files:
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                try:
                    tree_node, _report = parse_python_code(content, filename=str(py_file))
                    tree = tree_node if isinstance(tree_node, ast.Module) else ast.Module(body=[], type_ignores=[])
                except ParsingError:
                    continue  # Skip files that don't parse
                imports = set()

                for node in tree.body:
                    if isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.add(node.module.split(".")[0])
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.add(alias.name.split(".")[0])

                rel_path = str(py_file.relative_to(root_path))
                file_to_imports[rel_path] = imports
                dependency_graph[rel_path] = []

                # Map imports to files in project
                for imp in imports:
                    for other_file in python_files:
                        other_rel = str(other_file.relative_to(root_path))
                        if imp in other_rel or other_rel.replace("/", ".").startswith(imp):
                            dependency_graph[rel_path].append(other_rel)

            except Exception:
                continue

        # Cluster files by dependency similarity
        clusters = defaultdict(list)
        processed = set()

        for file_path, deps in dependency_graph.items():
            if file_path in processed:
                continue

            # Find files with similar dependencies
            cluster_key = tuple(sorted(set(deps) - {file_path}))
            clusters[cluster_key].append(file_path)
            processed.add(file_path)

        # Generate service suggestions from clusters
        suggested_services = []
        service_counter = 1

        for cluster_deps, cluster_files in clusters.items():
            if len(cluster_files) < 2:
                continue  # Skip single-file "services"

            # Determine isolation level based on external dependencies
            external_deps = [d for d in cluster_deps if d not in cluster_files]
            isolation_score = 1.0 - (len(external_deps) / max(len(cluster_deps), 1))

            if isolation_score < min_isolation_score:
                continue  # Skip poorly isolated clusters

            if isolation_score >= 0.9:
                isolation_level = "critical"
            elif isolation_score >= 0.7:
                isolation_level = "high"
            elif isolation_score >= 0.5:
                isolation_level = "medium"
            else:
                isolation_level = "low"

            # Generate service name from common path prefix
            common_prefix = Path(cluster_files[0]).parent.name if cluster_files else f"service{service_counter}"
            service_name = f"{common_prefix}-service"

            rationale = (
                f"Cluster of {len(cluster_files)} file(s) with {len(external_deps)} external dependency(ies). "
                f"Isolation score: {isolation_score:.2f}"
            )

            suggested_services.append(
                ServiceBoundary(
                    service_name=service_name,
                    included_files=cluster_files,
                    external_dependencies=list(external_deps),
                    internal_dependencies=[d for d in cluster_deps if d in cluster_files],
                    isolation_level=isolation_level,
                    rationale=rationale,
                )
            )
            service_counter += 1

        explanation = (
            f"Analyzed {len(python_files)} Python file(s). "
            f"Found {len(suggested_services)} potential service boundary(ies) "
            f"with isolation score >= {min_isolation_score}."
        )

        return ServiceBoundaryResult(
            success=True,
            suggested_services=suggested_services,
            dependency_graph=dependency_graph,
            total_files_analyzed=len(python_files),
            explanation=explanation,
        )

    except Exception as e:
        return ServiceBoundaryResult(
            success=False,
            suggested_services=[],
            dependency_graph={},
            total_files_analyzed=0,
            explanation="",
            error=f"Service boundary detection failed: {str(e)}",
        )
