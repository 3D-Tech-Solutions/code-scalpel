"""AST Utilities and Caching."""

import ast
import logging
from pathlib import Path

from code_scalpel.parsing.unified_parser import ParsingError, parse_python_code

logger = logging.getLogger("code_scalpel.mcp.ast")

# [20251216_PERF] v2.5.0 - Simple in-memory AST cache
# Key: file_path (str)
# Value: (mtime, ast_tree)
_AST_CACHE: dict[str, tuple[float, ast.AST]] = {}


def get_cached_ast(file_path: Path) -> ast.Module | None:
    """Retrieve cached AST if fresh, otherwise return None."""
    try:
        key = str(file_path.resolve())
        if key not in _AST_CACHE:
            return None

        mtime, tree = _AST_CACHE[key]
        current_mtime = file_path.stat().st_mtime
        if current_mtime > mtime:
            del _AST_CACHE[key]
            return None
        return tree  # type: ignore
    except OSError:
        return None


def cache_ast(file_path: Path, tree: ast.AST) -> None:
    """Cache an AST tree for path."""
    try:
        key = str(file_path.resolve())
        _AST_CACHE[key] = (file_path.stat().st_mtime, tree)
    except OSError:
        pass


def parse_file_cached(file_path: Path) -> ast.Module | None:
    """Parse a Python file with caching using unified parser."""
    # Check cache first
    cached = get_cached_ast(file_path)
    if cached is not None:
        return cached

    try:
        code = file_path.read_text(encoding="utf-8")
        try:
            tree, _report = parse_python_code(code, filename=str(file_path))
        except ParsingError:
            return None
        cache_ast(file_path, tree)
        return tree  # type: ignore
    except OSError:
        return None
