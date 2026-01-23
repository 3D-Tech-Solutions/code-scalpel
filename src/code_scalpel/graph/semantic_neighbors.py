"""
Semantic Neighbors - Find semantically related nodes in the graph.

[20251226_FEATURE] Pro tier feature for get_graph_neighborhood.

Provides semantic neighbor discovery beyond direct call relationships:
- Name similarity (e.g., process_order and validate_order)
- Docstring/comment similarity
- Shared parameter patterns
- Common return type patterns

Usage:
    from code_scalpel.graph.semantic_neighbors import SemanticNeighborFinder

    finder = SemanticNeighborFinder(project_root)
    neighbors = finder.find_semantic_neighbors("process_order", k=5)
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


@dataclass
class SemanticNeighbor:
    """A semantically related node."""

    node_id: str
    name: str
    file_path: str
    line: int
    similarity_score: float  # 0.0 - 1.0
    relationship_types: list[str]  # e.g., ["name_similar", "shared_params"]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SemanticNeighborResult:
    """Result of semantic neighbor search."""

    success: bool
    center_node: str
    neighbors: list[SemanticNeighbor]
    total_candidates: int
    search_scope: int  # Number of files searched
    error: str | None = None


@dataclass
class FunctionSignature:
    """Extracted function signature for comparison."""

    name: str
    file_path: str
    line: int
    parameters: list[str]
    return_annotation: str | None
    docstring: str | None
    decorators: list[str]


class SemanticNeighborFinder:
    """Finds semantically related nodes using various similarity metrics."""

    def __init__(self, project_root: str | Path):
        """Initialize finder with project root."""
        self.root = Path(project_root)
        self._function_cache: dict[str, FunctionSignature] = {}

    def find_semantic_neighbors(
        self,
        center_name: str,
        k: int = 10,
        min_similarity: float = 0.3,
        relationship_types: set[str] | None = None,
    ) -> SemanticNeighborResult:
        """
        Find k most semantically similar functions to the center function.

        Args:
            center_name: Name of the center function
            k: Maximum neighbors to return
            min_similarity: Minimum similarity score threshold
            relationship_types: Types of relationships to consider
                - "name_similar": Similar function names
                - "shared_params": Share parameter names/types
                - "docstring_similar": Similar docstrings
                - "decorator_similar": Share decorators
                - "prefix_match": Common prefix/suffix patterns

        Returns:
            SemanticNeighborResult with ranked neighbors
        """
        if relationship_types is None:
            relationship_types = {
                "name_similar",
                "shared_params",
                "docstring_similar",
                "decorator_similar",
                "prefix_match",
            }

        try:
            # Extract all function signatures from the project
            signatures = self._extract_all_signatures()

            # Find the center function
            center_sig = None
            for sig in signatures.values():
                if sig.name == center_name:
                    center_sig = sig
                    break

            if center_sig is None:
                return SemanticNeighborResult(
                    success=False,
                    center_node=center_name,
                    neighbors=[],
                    total_candidates=0,
                    search_scope=0,
                    error=f"Center function '{center_name}' not found",
                )

            # Calculate similarities
            candidates: list[tuple[float, SemanticNeighbor]] = []

            for _key, sig in signatures.items():
                if sig.name == center_name and sig.file_path == center_sig.file_path:
                    continue  # Skip self

                score, rel_types = self._calculate_similarity(center_sig, sig, relationship_types)

                if score >= min_similarity and rel_types:
                    node_id = self._make_node_id(sig)
                    candidates.append(
                        (
                            score,
                            SemanticNeighbor(
                                node_id=node_id,
                                name=sig.name,
                                file_path=sig.file_path,
                                line=sig.line,
                                similarity_score=score,
                                relationship_types=rel_types,
                                metadata={
                                    "parameters": sig.parameters,
                                    "decorators": sig.decorators,
                                },
                            ),
                        )
                    )

            # Sort by similarity and take top k
            candidates.sort(key=lambda x: x[0], reverse=True)
            top_neighbors = [n for _, n in candidates[:k]]

            return SemanticNeighborResult(
                success=True,
                center_node=center_name,
                neighbors=top_neighbors,
                total_candidates=len(candidates),
                search_scope=len(signatures),
            )

        except Exception as e:
            return SemanticNeighborResult(
                success=False,
                center_node=center_name,
                neighbors=[],
                total_candidates=0,
                search_scope=0,
                error=str(e),
            )

    def _extract_all_signatures(self) -> dict[str, FunctionSignature]:
        """Extract all function signatures from Python files."""
        if self._function_cache:
            return self._function_cache

        signatures: dict[str, FunctionSignature] = {}

        # Exclude common non-source directories
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
            "htmlcov",
        }

        for py_file in self.root.rglob("*.py"):
            # Skip excluded directories
            if any(part in exclude_dirs for part in py_file.parts):
                continue

            try:
                code = py_file.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(code)

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        sig = self._extract_signature(node, py_file, code)
                        key = f"{py_file}:{sig.name}:{sig.line}"
                        signatures[key] = sig

            except (SyntaxError, UnicodeDecodeError):
                continue

        self._function_cache = signatures
        return signatures

    def _extract_signature(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        file_path: Path,
        source_code: str,
    ) -> FunctionSignature:
        """Extract signature information from a function node."""
        # Get parameters
        params = []
        for arg in node.args.args:
            param_name = arg.arg
            if arg.annotation:
                try:
                    param_name += f": {ast.unparse(arg.annotation)}"
                except Exception:
                    pass
            params.append(param_name)

        # Get return annotation
        return_ann = None
        if node.returns:
            try:
                return_ann = ast.unparse(node.returns)
            except Exception:
                pass

        # Get docstring
        docstring = ast.get_docstring(node)

        # Get decorators
        decorators = []
        for dec in node.decorator_list:
            try:
                decorators.append(ast.unparse(dec))
            except Exception:
                if isinstance(dec, ast.Name):
                    decorators.append(dec.id)
                elif isinstance(dec, ast.Attribute):
                    decorators.append(dec.attr)

        return FunctionSignature(
            name=node.name,
            file_path=str(file_path.relative_to(self.root)),
            line=node.lineno,
            parameters=params,
            return_annotation=return_ann,
            docstring=docstring,
            decorators=decorators,
        )

    def _calculate_similarity(
        self,
        center: FunctionSignature,
        candidate: FunctionSignature,
        relationship_types: set[str],
    ) -> tuple[float, list[str]]:
        """Calculate similarity between two function signatures."""
        scores: list[tuple[float, str]] = []

        if "name_similar" in relationship_types:
            name_sim = self._name_similarity(center.name, candidate.name)
            if name_sim > 0.3:
                scores.append((name_sim * 0.4, "name_similar"))

        if "prefix_match" in relationship_types:
            prefix_sim = self._prefix_suffix_similarity(center.name, candidate.name)
            if prefix_sim > 0.5:
                scores.append((prefix_sim * 0.3, "prefix_match"))

        if "shared_params" in relationship_types:
            param_sim = self._parameter_similarity(center.parameters, candidate.parameters)
            if param_sim > 0.3:
                scores.append((param_sim * 0.2, "shared_params"))

        if "docstring_similar" in relationship_types and center.docstring and candidate.docstring:
            doc_sim = self._text_similarity(center.docstring, candidate.docstring)
            if doc_sim > 0.3:
                scores.append((doc_sim * 0.2, "docstring_similar"))

        if "decorator_similar" in relationship_types:
            dec_sim = self._set_similarity(set(center.decorators), set(candidate.decorators))
            if dec_sim > 0.5:
                scores.append((dec_sim * 0.2, "decorator_similar"))

        if not scores:
            return 0.0, []

        total_score = sum(s for s, _ in scores)
        rel_types = [t for _, t in scores]

        return min(total_score, 1.0), rel_types

    def _name_similarity(self, name1: str, name2: str) -> float:
        """Calculate name similarity using SequenceMatcher."""
        return SequenceMatcher(None, name1.lower(), name2.lower()).ratio()

    def _prefix_suffix_similarity(self, name1: str, name2: str) -> float:
        """Check for common prefixes/suffixes in names."""
        # Split camelCase and snake_case
        parts1 = self._split_name(name1)
        parts2 = self._split_name(name2)

        if not parts1 or not parts2:
            return 0.0

        # Check shared parts
        shared = set(parts1) & set(parts2)
        if not shared:
            return 0.0

        total = set(parts1) | set(parts2)
        return len(shared) / len(total)

    def _split_name(self, name: str) -> list[str]:
        """Split a name into parts (snake_case and camelCase)."""
        # Handle snake_case
        if "_" in name:
            parts = name.lower().split("_")
        else:
            # Handle camelCase
            parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)", name)
            parts = [p.lower() for p in parts]
        return [p for p in parts if p]

    def _parameter_similarity(self, params1: list[str], params2: list[str]) -> float:
        """Calculate similarity between parameter lists."""
        if not params1 or not params2:
            return 0.0

        # Extract just parameter names (without type annotations)
        names1 = set(p.split(":")[0].strip() for p in params1)
        names2 = set(p.split(":")[0].strip() for p in params2)

        # Remove 'self' and 'cls' from comparison
        names1 -= {"self", "cls"}
        names2 -= {"self", "cls"}

        if not names1 or not names2:
            return 0.0

        return self._set_similarity(names1, names2)

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity between docstrings."""
        # Normalize and tokenize
        words1 = set(re.findall(r"\w+", text1.lower()))
        words2 = set(re.findall(r"\w+", text2.lower()))

        # Remove common stop words
        stop_words = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "and",
            "or",
            "to",
            "of",
            "in",
            "for",
        }
        words1 -= stop_words
        words2 -= stop_words

        if not words1 or not words2:
            return 0.0

        return self._set_similarity(words1, words2)

    def _set_similarity(self, set1: set[str], set2: set[str]) -> float:
        """Jaccard similarity between two sets."""
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

    def _make_node_id(self, sig: FunctionSignature) -> str:
        """Create a canonical node ID from a signature."""
        module = sig.file_path.replace("/", ".").replace("\\", ".")
        if module.endswith(".py"):
            module = module[:-3]
        return f"python::{module}::function::{sig.name}"


def find_semantic_neighbors(
    project_root: str | Path,
    center_name: str,
    k: int = 10,
    min_similarity: float = 0.3,
) -> SemanticNeighborResult:
    """Convenience function to find semantic neighbors."""
    finder = SemanticNeighborFinder(project_root)
    return finder.find_semantic_neighbors(center_name, k, min_similarity)
