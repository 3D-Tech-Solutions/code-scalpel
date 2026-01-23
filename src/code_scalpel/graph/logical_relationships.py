"""
Logical Relationships - Detect logical relationships between code elements.

[20251226_FEATURE] Pro tier feature for get_graph_neighborhood.

Detects non-call relationships between functions:
- Sibling functions (same module, similar concerns)
- Shared file context (defined in same file)
- Test-implementation pairs
- Interface-implementation relationships
- Helper function patterns

Usage:
    from code_scalpel.graph.logical_relationships import LogicalRelationshipDetector

    detector = LogicalRelationshipDetector(project_root)
    relationships = detector.find_relationships("my_function")
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class LogicalRelationship:
    """A logical relationship between code elements."""

    source_node: str
    target_node: str
    relationship_type: str  # e.g., "sibling", "test_for", "helper_of"
    confidence: float  # 0.0 - 1.0
    evidence: str  # Description of why this relationship exists
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LogicalRelationshipResult:
    """Result of logical relationship detection."""

    success: bool
    center_node: str
    relationships: list[LogicalRelationship]
    total_found: int
    error: str | None = None


@dataclass
class FunctionContext:
    """Context information for a function."""

    name: str
    file_path: str
    line: int
    module: str
    class_name: str | None  # If method
    decorators: list[str]
    docstring: str | None
    is_test: bool
    is_private: bool
    is_dunder: bool


class LogicalRelationshipDetector:
    """Detects logical relationships between code elements."""

    # Test file patterns
    TEST_FILE_PATTERNS = {
        r"test_.*\.py$",
        r".*_test\.py$",
        r"tests?\.py$",
    }

    # Test function patterns
    TEST_FUNCTION_PATTERNS = {
        r"^test_",
        r"^Test",
    }

    # Helper function patterns (typically private)
    HELPER_PATTERNS = {
        r"^_(?!_)",  # Single underscore prefix (not dunder)
    }

    def __init__(self, project_root: str | Path):
        """Initialize detector with project root."""
        self.root = Path(project_root)
        self._context_cache: dict[str, FunctionContext] = {}

    def find_relationships(
        self,
        center_name: str,
        relationship_types: set[str] | None = None,
        max_relationships: int = 20,
    ) -> LogicalRelationshipResult:
        """
        Find logical relationships for a function.

        Args:
            center_name: Name of the center function
            relationship_types: Types of relationships to detect
                - "sibling": Functions in same module with similar purpose
                - "test_for": Test functions that test this function
                - "tested_by": Implementation tested by this test
                - "helper_of": Private helper functions used by this function
                - "uses_helper": Public function that uses this helper
                - "same_class": Other methods in the same class
                - "interface_impl": Interface implementation relationships
            max_relationships: Maximum relationships to return

        Returns:
            LogicalRelationshipResult with detected relationships
        """
        if relationship_types is None:
            relationship_types = {
                "sibling",
                "test_for",
                "tested_by",
                "helper_of",
                "uses_helper",
                "same_class",
            }

        try:
            # Extract all function contexts
            contexts = self._extract_all_contexts()

            # Find the center function
            center_ctx = None
            for ctx in contexts.values():
                if ctx.name == center_name:
                    center_ctx = ctx
                    break

            if center_ctx is None:
                return LogicalRelationshipResult(
                    success=False,
                    center_node=center_name,
                    relationships=[],
                    total_found=0,
                    error=f"Center function '{center_name}' not found",
                )

            relationships: list[LogicalRelationship] = []

            # Find test relationships
            if "test_for" in relationship_types or "tested_by" in relationship_types:
                test_rels = self._find_test_relationships(center_ctx, contexts, relationship_types)
                relationships.extend(test_rels)

            # Find sibling relationships
            if "sibling" in relationship_types:
                sibling_rels = self._find_sibling_relationships(center_ctx, contexts)
                relationships.extend(sibling_rels)

            # Find helper relationships
            if "helper_of" in relationship_types or "uses_helper" in relationship_types:
                helper_rels = self._find_helper_relationships(center_ctx, contexts, relationship_types)
                relationships.extend(helper_rels)

            # Find same-class relationships
            if "same_class" in relationship_types:
                class_rels = self._find_same_class_relationships(center_ctx, contexts)
                relationships.extend(class_rels)

            # Sort by confidence and limit
            relationships.sort(key=lambda r: r.confidence, reverse=True)
            relationships = relationships[:max_relationships]

            return LogicalRelationshipResult(
                success=True,
                center_node=center_name,
                relationships=relationships,
                total_found=len(relationships),
            )

        except Exception as e:
            return LogicalRelationshipResult(
                success=False,
                center_node=center_name,
                relationships=[],
                total_found=0,
                error=str(e),
            )

    def _extract_all_contexts(self) -> dict[str, FunctionContext]:
        """Extract context for all functions in the project."""
        if self._context_cache:
            return self._context_cache

        contexts: dict[str, FunctionContext] = {}

        exclude_dirs = {
            "__pycache__",
            ".git",
            "venv",
            ".venv",
            "node_modules",
            "dist",
            "build",
            ".tox",
            ".pytest_cache",
        }

        for py_file in self.root.rglob("*.py"):
            if any(part in exclude_dirs for part in py_file.parts):
                continue

            try:
                rel_path = str(py_file.relative_to(self.root))
                is_test_file = any(re.search(pattern, rel_path) for pattern in self.TEST_FILE_PATTERNS)

                code = py_file.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(code)

                # Extract module name
                module = rel_path.replace("/", ".").replace("\\", ".")
                if module.endswith(".py"):
                    module = module[:-3]

                self._extract_functions_from_tree(tree, contexts, rel_path, module, is_test_file, None)

            except (SyntaxError, UnicodeDecodeError):
                continue

        self._context_cache = contexts
        return contexts

    def _extract_functions_from_tree(
        self,
        tree: ast.AST,
        contexts: dict[str, FunctionContext],
        file_path: str,
        module: str,
        is_test_file: bool,
        class_name: str | None,
    ) -> None:
        """Extract function contexts from an AST tree."""
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                # Recurse into class
                self._extract_functions_from_tree(node, contexts, file_path, module, is_test_file, node.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                ctx = self._make_function_context(node, file_path, module, is_test_file, class_name)
                key = f"{file_path}:{ctx.name}:{ctx.line}"
                contexts[key] = ctx

    def _make_function_context(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        file_path: str,
        module: str,
        is_test_file: bool,
        class_name: str | None,
    ) -> FunctionContext:
        """Create a FunctionContext from an AST node."""
        name = node.name

        # Get decorators
        decorators = []
        for dec in node.decorator_list:
            try:
                decorators.append(ast.unparse(dec))
            except Exception:
                if isinstance(dec, ast.Name):
                    decorators.append(dec.id)

        # Check patterns
        is_test = is_test_file or any(re.match(pattern, name) for pattern in self.TEST_FUNCTION_PATTERNS)
        is_private = name.startswith("_") and not name.startswith("__")
        is_dunder = name.startswith("__") and name.endswith("__")

        return FunctionContext(
            name=name,
            file_path=file_path,
            line=node.lineno,
            module=module,
            class_name=class_name,
            decorators=decorators,
            docstring=ast.get_docstring(node),
            is_test=is_test,
            is_private=is_private,
            is_dunder=is_dunder,
        )

    def _find_test_relationships(
        self,
        center: FunctionContext,
        contexts: dict[str, FunctionContext],
        relationship_types: set[str],
    ) -> list[LogicalRelationship]:
        """Find test-implementation relationships."""
        relationships = []

        if center.is_test and "tested_by" in relationship_types:
            # This is a test function - find what it tests
            # Extract the target name from test_xxx pattern
            match = re.match(r"^test_(.+)$", center.name)
            if match:
                target_name = match.group(1)
                for ctx in contexts.values():
                    if ctx.name == target_name and not ctx.is_test:
                        relationships.append(
                            LogicalRelationship(
                                source_node=self._make_node_id(center),
                                target_node=self._make_node_id(ctx),
                                relationship_type="tested_by",
                                confidence=0.85,
                                evidence=f"Test function 'test_{target_name}' likely tests '{target_name}'",
                                metadata={"target_file": ctx.file_path},
                            )
                        )

        elif not center.is_test and "test_for" in relationship_types:
            # This is an implementation - find its tests
            test_name = f"test_{center.name}"
            for ctx in contexts.values():
                if ctx.name == test_name and ctx.is_test:
                    relationships.append(
                        LogicalRelationship(
                            source_node=self._make_node_id(center),
                            target_node=self._make_node_id(ctx),
                            relationship_type="test_for",
                            confidence=0.85,
                            evidence=f"Function '{center.name}' is likely tested by 'test_{center.name}'",
                            metadata={"test_file": ctx.file_path},
                        )
                    )

        return relationships

    def _find_sibling_relationships(
        self,
        center: FunctionContext,
        contexts: dict[str, FunctionContext],
    ) -> list[LogicalRelationship]:
        """Find sibling functions in the same module."""
        relationships = []

        for ctx in contexts.values():
            if ctx.name == center.name and ctx.file_path == center.file_path:
                continue  # Skip self

            # Same file = strong sibling relationship
            if ctx.file_path == center.file_path:
                # Skip dunder methods and tests
                if ctx.is_dunder or (ctx.is_test and not center.is_test):
                    continue

                confidence = 0.7
                evidence = f"Defined in same file: {center.file_path}"

                # Higher confidence if same class
                if ctx.class_name and ctx.class_name == center.class_name:
                    confidence = 0.85
                    evidence = f"Methods in same class: {center.class_name}"

                relationships.append(
                    LogicalRelationship(
                        source_node=self._make_node_id(center),
                        target_node=self._make_node_id(ctx),
                        relationship_type="sibling",
                        confidence=confidence,
                        evidence=evidence,
                    )
                )

        return relationships

    def _find_helper_relationships(
        self,
        center: FunctionContext,
        contexts: dict[str, FunctionContext],
        relationship_types: set[str],
    ) -> list[LogicalRelationship]:
        """Find helper function relationships."""
        relationships = []

        if center.is_private and "uses_helper" in relationship_types:
            # This is a helper - find public functions in same module
            for ctx in contexts.values():
                if ctx.file_path == center.file_path and not ctx.is_private and not ctx.is_dunder:
                    relationships.append(
                        LogicalRelationship(
                            source_node=self._make_node_id(center),
                            target_node=self._make_node_id(ctx),
                            relationship_type="uses_helper",
                            confidence=0.6,
                            evidence=f"Helper '{center.name}' may be used by '{ctx.name}'",
                        )
                    )

        elif not center.is_private and "helper_of" in relationship_types:
            # This is public - find helpers in same module
            for ctx in contexts.values():
                if ctx.file_path == center.file_path and ctx.is_private:
                    relationships.append(
                        LogicalRelationship(
                            source_node=self._make_node_id(center),
                            target_node=self._make_node_id(ctx),
                            relationship_type="helper_of",
                            confidence=0.6,
                            evidence=f"'{center.name}' may use helper '{ctx.name}'",
                        )
                    )

        return relationships

    def _find_same_class_relationships(
        self,
        center: FunctionContext,
        contexts: dict[str, FunctionContext],
    ) -> list[LogicalRelationship]:
        """Find other methods in the same class."""
        relationships = []

        if not center.class_name:
            return relationships

        for ctx in contexts.values():
            if (
                ctx.class_name == center.class_name
                and ctx.file_path == center.file_path
                and ctx.name != center.name
                and not ctx.is_dunder
            ):

                relationships.append(
                    LogicalRelationship(
                        source_node=self._make_node_id(center),
                        target_node=self._make_node_id(ctx),
                        relationship_type="same_class",
                        confidence=0.8,
                        evidence=f"Both methods of class '{center.class_name}'",
                        metadata={"class_name": center.class_name},
                    )
                )

        return relationships

    def _make_node_id(self, ctx: FunctionContext) -> str:
        """Create a canonical node ID from a context."""
        return f"python::{ctx.module}::function::{ctx.name}"


def find_logical_relationships(
    project_root: str | Path,
    center_name: str,
    max_relationships: int = 20,
) -> LogicalRelationshipResult:
    """Convenience function to find logical relationships."""
    detector = LogicalRelationshipDetector(project_root)
    return detector.find_relationships(center_name, max_relationships=max_relationships)
