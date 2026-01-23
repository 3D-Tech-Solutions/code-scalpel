# Project Crawler - Whole-project Python analysis tool.
#
# [20251224_REFACTOR] Moved from code_scalpel/project_crawler.py to
# code_scalpel/analysis/project_crawler.py as part of Issue #3
# in PROJECT_REORG_REFACTOR.md Phase 1.
#
# Crawls an entire project directory, analyzes all Python files, and generates
# comprehensive metrics including:
# - Structure analysis (classes, functions, imports)
# - Cyclomatic complexity estimation
# - Lines of code counts
# - Complexity hotspot detection
#
# This module integrates with Code Scalpel's existing AST analysis tools
# and can be used standalone or via the MCP server.
#
# Usage:
#     from code_scalpel.analysis import ProjectCrawler
#
#     crawler = ProjectCrawler("/path/to/project")
#     result = crawler.crawl()
#     print(result.summary)
#
#     # Generate markdown report
#     report = crawler.generate_report()


from __future__ import annotations

import ast
import datetime
import multiprocessing as mp
import os
import re
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, TypedDict


class CrawlResultDict(TypedDict, total=False):
    """Crawl results dictionary for JSON serialization."""

    root_path: str
    timestamp: str
    summary: dict[str, Any]
    files: list[dict[str, Any]]  # FileResultDict
    errors: list[dict[str, Any]]  # FileResultDict


# Default directories to exclude from crawling
DEFAULT_EXCLUDE_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "venv",
        ".venv",
        "env",
        ".env",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
        "dist",
        "build",
        "egg-info",
        ".egg-info",
        ".tox",
        ".nox",
        "htmlcov",
        "site-packages",
    }
)

# Default complexity threshold for warnings
DEFAULT_COMPLEXITY_THRESHOLD: int = 10


def _analyze_file_worker(file_path: str) -> FileAnalysisResult:
    """ProcessPool worker entrypoint for analyzing a single file."""
    crawler = ProjectCrawler(
        root_path=Path(file_path).parent,
        # Worker only analyzes the given file; config is minimal and deterministic.
        respect_gitignore=False,
    )
    return crawler._analyze_file(file_path)


@dataclass
class FunctionInfo:
    """
    Information about a function or method.
    """

    name: str
    lineno: int
    complexity: int
    is_method: bool = False
    class_name: str | None = None

    @property
    def qualified_name(self) -> str:
        """Return the fully qualified name."""
        if self.class_name:
            return f"{self.class_name}.{self.name}"
        return self.name


@dataclass
class ClassInfo:
    """
    Information about a class.
    """

    name: str
    lineno: int
    methods: list[FunctionInfo] = field(default_factory=list)
    bases: list[str] = field(default_factory=list)


@dataclass
class FileAnalysisResult:
    """
    Result of analyzing a single file.
    """

    path: str
    status: str  # "success" or "error"
    language: str = "python"
    lines_of_code: int = 0
    complexity_score: int = 0
    functions: list[FunctionInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    complexity_warnings: list[FunctionInfo] = field(default_factory=list)
    error: str | None = None

    @property
    def total_functions(self) -> int:
        """Total number of functions including class methods."""
        return len(self.functions) + sum(len(c.methods) for c in self.classes)


@dataclass
class CrawlResult:
    """
    Result of crawling an entire project.
    """

    root_path: str
    timestamp: str
    files_analyzed: list[FileAnalysisResult] = field(default_factory=list)
    files_with_errors: list[FileAnalysisResult] = field(default_factory=list)

    @property
    def total_files(self) -> int:
        """Total number of files scanned."""
        return len(self.files_analyzed) + len(self.files_with_errors)

    @property
    def total_lines_of_code(self) -> int:
        """Total lines of code across all files."""
        return sum(f.lines_of_code for f in self.files_analyzed)

    @property
    def total_functions(self) -> int:
        """Total number of functions across all files."""
        return sum(f.total_functions for f in self.files_analyzed)

    @property
    def total_classes(self) -> int:
        """Total number of classes across all files."""
        return sum(len(f.classes) for f in self.files_analyzed)

    @property
    def all_complexity_warnings(self) -> list[tuple[str, FunctionInfo]]:
        """All complexity warnings with file paths."""
        warnings = []
        for file_result in self.files_analyzed:
            for func in file_result.complexity_warnings:
                warnings.append((file_result.path, func))
        return warnings

    @property
    def summary(self) -> dict[str, Any]:
        """Summary statistics."""
        return {
            "root_path": self.root_path,
            "timestamp": self.timestamp,
            "total_files": self.total_files,
            "successful_files": len(self.files_analyzed),
            "failed_files": len(self.files_with_errors),
            "total_lines_of_code": self.total_lines_of_code,
            "total_functions": self.total_functions,
            "total_classes": self.total_classes,
            "complexity_warnings": len(self.all_complexity_warnings),
        }


class CodeAnalyzerVisitor(ast.NodeVisitor):
    """
    AST visitor that extracts code metrics.
    """

    def __init__(self, complexity_threshold: int = DEFAULT_COMPLEXITY_THRESHOLD):
        self.complexity_threshold = complexity_threshold
        self.functions: list[FunctionInfo] = []
        self.classes: list[ClassInfo] = []
        self.imports: list[str] = []
        self.complexity_warnings: list[FunctionInfo] = []
        self._current_class: ClassInfo | None = None
        # self._nesting_depth: int = 0
        # self._max_nesting_depth: int = 0
        # self.global_variables: list[str] = []
        # self.constants: list[str] = []
        # self.decorators_used: set[str] = set()
        # self.type_annotations_count: int = 0

    def visit_Import(self, node: ast.Import) -> None:
        """Handle import statements."""
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Handle from ... import statements."""
        if node.module:
            self.imports.append(node.module)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Handle class definitions."""
        bases: list[str] = [base_name for base in node.bases if (base_name := self._get_base_name(base)) is not None]
        class_info = ClassInfo(
            name=node.name,
            lineno=node.lineno,
            bases=bases,
        )
        self.classes.append(class_info)

        # Visit class body with context
        old_class = self._current_class
        self._current_class = class_info
        self.generic_visit(node)
        self._current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Handle function definitions."""
        self._process_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Handle async function definitions."""
        self._process_function(node)

    def _process_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Process a function or async function definition."""
        complexity = self._calculate_complexity(node)

        func_info = FunctionInfo(
            name=node.name,
            lineno=node.lineno,
            complexity=complexity,
            is_method=self._current_class is not None,
            class_name=self._current_class.name if self._current_class else None,
        )

        if self._current_class:
            self._current_class.methods.append(func_info)
        else:
            self.functions.append(func_info)

        if complexity > self.complexity_threshold:
            self.complexity_warnings.append(func_info)

        self.generic_visit(node)

    def _calculate_complexity(self, node: ast.AST) -> int:
        """
        Calculate cyclomatic complexity.

        Complexity = 1 + number of decision points (if, for, while, try, etc.)
        """

        score = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With)):
                score += 1
            elif isinstance(child, ast.Try):
                score += 1
            elif isinstance(child, ast.ExceptHandler):
                score += 1
            elif isinstance(child, ast.BoolOp):
                # and/or add decision points
                score += len(child.values) - 1
            elif isinstance(child, ast.comprehension):
                # List/dict/set comprehensions with if clauses
                score += len(child.ifs)
            # elif isinstance(child, ast.Match):  # Python 3.10+
            #     score += len(child.cases)
            # elif isinstance(child, ast.IfExp):  # Ternary expressions
            #     score += 1
            # elif isinstance(child, ast.Assert):
            #     score += 1  # Optional: count assertions
        return score

    @staticmethod
    def _get_base_name(node: ast.expr) -> str | None:
        """Extract base class name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return None


class ProjectCrawler:
    """
    Crawls a project directory and analyzes all Python files.

    Example:
        crawler = ProjectCrawler("/path/to/project")
        result = crawler.crawl()
        print(f"Analyzed {result.total_files} files")
        print(f"Total LOC: {result.total_lines_of_code}")
    """

    def __init__(
        self,
        root_path: str | Path,
        exclude_dirs: frozenset[str] | None = None,
        complexity_threshold: int = DEFAULT_COMPLEXITY_THRESHOLD,
        max_files: int | None = None,
        max_depth: int | None = None,
        respect_gitignore: bool = False,
        include_extensions: tuple[str, ...] | None = None,
        parallelism: str = "none",  # none|threads|processes
        enable_cache: bool = False,
    ):
        """
        Initialize the project crawler.

        Args:
            root_path: Root directory to crawl
            exclude_dirs: Directory names to exclude (uses defaults if None)
            complexity_threshold: Complexity score that triggers a warning
        """
        self.root_path = Path(root_path).resolve()
        self.exclude_dirs = exclude_dirs or DEFAULT_EXCLUDE_DIRS
        self.complexity_threshold = complexity_threshold
        self.max_files = max_files
        self.max_depth = max_depth
        self.respect_gitignore = respect_gitignore
        self.include_extensions: tuple[str, ...] = include_extensions or (
            ".py",
            ".js",
            ".jsx",
            ".ts",
            ".tsx",
            ".java",
        )
        self.parallelism = parallelism
        self.enable_cache = enable_cache
        self._gitignore_patterns: list[str] = []

        self._cache_dir = self.root_path / ".scalpel_cache"
        self._cache_file = self._cache_dir / "crawl_cache_v1.json"
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache: dict[str, Any] = {}

        if not self.root_path.exists():
            raise ValueError(f"Path does not exist: {self.root_path}")
        if not self.root_path.is_dir():
            raise ValueError(f"Path is not a directory: {self.root_path}")

        # [20251225_FEATURE] Minimal .gitignore support for tiered crawling.
        if self.respect_gitignore:
            gitignore_file = self.root_path / ".gitignore"
            if gitignore_file.exists() and gitignore_file.is_file():
                for raw in gitignore_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    if line.startswith("!"):
                        # Negation patterns are intentionally ignored in this minimal implementation.
                        continue
                    self._gitignore_patterns.append(line)

        if self.enable_cache:
            self._cache_dir.mkdir(exist_ok=True)
            self._cache = self._load_cache()

    def _load_cache(self) -> dict[str, Any]:
        try:
            import json

            if self._cache_file.exists() and self._cache_file.is_file():
                return json.loads(self._cache_file.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {"version": 1, "files": {}}

    def _save_cache(self) -> None:
        if not self.enable_cache:
            return
        try:
            import json

            self._cache["saved_at"] = datetime.datetime.now().isoformat()
            self._cache_file.write_text(json.dumps(self._cache), encoding="utf-8")
        except Exception:
            # Best-effort caching only
            return

    def _detect_language(self, path: Path) -> str:
        ext = path.suffix.lower()
        if ext == ".py":
            return "python"
        if ext in (".js", ".jsx"):
            return "javascript"
        if ext in (".ts", ".tsx"):
            return "typescript"
        if ext == ".java":
            return "java"
        return "unknown"

    def _estimate_complexity_text(self, content: str, language: str) -> int:
        # Heuristic, deterministic, and cheap. Intended for "basic complexity metrics".
        lowered = content.lower()
        score = 1

        if language in ("javascript", "typescript", "java"):
            # Control flow keywords
            keywords = [
                " if ",
                " for ",
                " while ",
                " catch ",
                " case ",
                "&&",
                "||",
                "?",
            ]
            for kw in keywords:
                score += lowered.count(kw)
            return score

        # Python-ish fallback
        keywords = [" if ", " for ", " while ", " except ", " and ", " or ", " with "]
        for kw in keywords:
            score += lowered.count(kw)
        return score

    def _cache_key_for(self, rel_path: str) -> str:
        # Stable key regardless of OS path separators
        return rel_path.replace("\\", "/")

    def _try_load_cached(self, file_path: Path, rel_path: str) -> FileAnalysisResult | None:
        if not self.enable_cache:
            return None

        try:
            st = file_path.stat()
        except Exception:
            return None

        cache_files = self._cache.get("files", {})
        key = self._cache_key_for(rel_path)
        entry = cache_files.get(key)
        if not isinstance(entry, dict):
            return None

        if entry.get("mtime") == st.st_mtime and entry.get("size") == st.st_size:
            try:
                self._cache_hits += 1
                return FileAnalysisResult(
                    path=str(file_path),
                    language=str(entry.get("language") or "unknown"),
                    status=str(entry.get("status") or "success"),
                    lines_of_code=int(entry.get("lines_of_code") or 0),
                    complexity_score=int(entry.get("complexity_score") or 0),
                    functions=[
                        FunctionInfo(
                            name=f["name"],
                            lineno=int(f["lineno"]),
                            complexity=int(f["complexity"]),
                            is_method=bool(f.get("is_method", False)),
                            class_name=f.get("class_name"),
                        )
                        for f in (entry.get("functions") or [])
                        if isinstance(f, dict)
                    ],
                    classes=[
                        ClassInfo(
                            name=c["name"],
                            lineno=int(c["lineno"]),
                            methods=[
                                FunctionInfo(
                                    name=m["name"],
                                    lineno=int(m["lineno"]),
                                    complexity=int(m["complexity"]),
                                    is_method=True,
                                    class_name=c["name"],
                                )
                                for m in (c.get("methods") or [])
                                if isinstance(m, dict)
                            ],
                            bases=[str(b) for b in (c.get("bases") or [])],
                        )
                        for c in (entry.get("classes") or [])
                        if isinstance(c, dict)
                    ],
                    imports=[str(x) for x in (entry.get("imports") or [])],
                    complexity_warnings=[
                        FunctionInfo(
                            name=w["name"],
                            lineno=int(w["lineno"]),
                            complexity=int(w["complexity"]),
                        )
                        for w in (entry.get("complexity_warnings") or [])
                        if isinstance(w, dict)
                    ],
                    error=entry.get("error"),
                )
            except Exception:
                return None

        return None

    def _store_cache_entry(self, file_path: Path, rel_path: str, result: FileAnalysisResult) -> None:
        if not self.enable_cache:
            return
        try:

            st = file_path.stat()
            key = self._cache_key_for(rel_path)
            files = self._cache.setdefault("files", {})
            files[key] = {
                "mtime": st.st_mtime,
                "size": st.st_size,
                "language": result.language,
                "status": result.status,
                "lines_of_code": result.lines_of_code,
                "complexity_score": result.complexity_score,
                "imports": result.imports,
                "functions": [
                    {
                        "name": f.name,
                        "lineno": f.lineno,
                        "complexity": f.complexity,
                        "is_method": f.is_method,
                        "class_name": f.class_name,
                    }
                    for f in result.functions
                ],
                "classes": [
                    {
                        "name": c.name,
                        "lineno": c.lineno,
                        "bases": c.bases,
                        "methods": [
                            {
                                "name": m.name,
                                "lineno": m.lineno,
                                "complexity": m.complexity,
                            }
                            for m in c.methods
                        ],
                    }
                    for c in result.classes
                ],
                "complexity_warnings": [
                    {"name": w.name, "lineno": w.lineno, "complexity": w.complexity} for w in result.complexity_warnings
                ],
                "error": result.error,
            }
        except Exception:
            return

    def _is_gitignored(self, rel_path: Path, *, is_dir: bool) -> bool:
        if not self._gitignore_patterns:
            return False
        rel_posix = rel_path.as_posix().lstrip("./")
        for pattern in self._gitignore_patterns:
            pat = pattern
            if pat.endswith("/"):
                if not is_dir:
                    continue
                pat = pat[:-1]
            if "/" in pat:
                if fnmatch(rel_posix, pat):
                    return True
            else:
                if fnmatch(rel_path.name, pat):
                    return True
        return False

    def crawl(self) -> CrawlResult:
        """
        Crawl the project and analyze all Python files.

        Returns:
            CrawlResult with analysis data for all files
        """
        result = CrawlResult(
            root_path=str(self.root_path),
            timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        files_to_analyze: list[tuple[Path, str]] = []
        analyzed_files = 0
        reached_limit = False

        for root, dirs, files in os.walk(self.root_path):
            rel_dir = Path(root).resolve().relative_to(self.root_path)
            depth = len(rel_dir.parts)
            if self.max_depth is not None and depth >= self.max_depth:
                dirs[:] = []
            else:
                filtered_dirs: list[str] = []
                for d in dirs:
                    if d in self.exclude_dirs:
                        continue
                    rel_child = rel_dir / d
                    if self._is_gitignored(rel_child, is_dir=True):
                        continue
                    filtered_dirs.append(d)
                dirs[:] = filtered_dirs

            for filename in files:
                rel_file = rel_dir / filename
                if self._is_gitignored(rel_file, is_dir=False):
                    continue

                if Path(filename).suffix.lower() in self.include_extensions:
                    if self.max_files is not None and analyzed_files >= self.max_files:
                        reached_limit = True
                        dirs[:] = []
                        break
                    analyzed_files += 1
                    file_path = Path(root) / filename
                    rel_path = str((Path(root) / filename).resolve().relative_to(self.root_path))
                    files_to_analyze.append((file_path, rel_path))

            if reached_limit:
                break

        # Analyze discovered files (with optional caching/parallelism)
        analyzed_results: list[FileAnalysisResult] = []

        def _analyze_one(path_and_rel: tuple[Path, str]) -> FileAnalysisResult:
            fp, relp = path_and_rel
            cached = self._try_load_cached(fp, relp)
            if cached is not None:
                return cached
            self._cache_misses += 1
            res = self._analyze_file(str(fp))
            self._store_cache_entry(fp, relp, res)
            return res

        parallelism = self.parallelism
        if parallelism == "threads":
            with ThreadPoolExecutor(max_workers=min(32, (os.cpu_count() or 4) + 4)) as ex:
                futs = {ex.submit(_analyze_one, item): item for item in files_to_analyze}
                for fut in as_completed(futs):
                    analyzed_results.append(fut.result())
        elif parallelism == "processes":
            # Process-based parallelism for "distributed" worker mode (local machine).
            # Cache hits are resolved in the parent process; cache misses are analyzed in workers.
            hits: list[FileAnalysisResult] = []
            misses: list[tuple[Path, str]] = []
            for fp, relp in files_to_analyze:
                cached = self._try_load_cached(fp, relp)
                if cached is not None:
                    hits.append(cached)
                else:
                    self._cache_misses += 1
                    misses.append((fp, relp))

            analyzed_results.extend(hits)

            if misses:
                ctx = mp.get_context("spawn")
                with ProcessPoolExecutor(
                    max_workers=max(2, os.cpu_count() or 2),
                    mp_context=ctx,
                ) as ex:
                    futs = {ex.submit(_analyze_file_worker, str(fp)): (fp, relp) for fp, relp in misses}
                    for fut in as_completed(futs):
                        fp, relp = futs[fut]
                        res = fut.result()
                        self._store_cache_entry(fp, relp, res)
                        analyzed_results.append(res)
        else:
            for item in files_to_analyze:
                analyzed_results.append(_analyze_one(item))

        # Deterministic ordering
        analyzed_results.sort(key=lambda r: os.path.normpath(r.path))
        for file_result in analyzed_results:
            if file_result.status == "success":
                result.files_analyzed.append(file_result)
            else:
                result.files_with_errors.append(file_result)

        self._save_cache()
        return result

    def _analyze_file(self, file_path: str) -> FileAnalysisResult:
        """
        Analyze a single Python file.

        Args:
            file_path: Path to the Python file

        Returns:
            FileAnalysisResult with metrics
        """
        try:
            path_obj = Path(file_path)
            language = self._detect_language(path_obj)

            with open(file_path, encoding="utf-8", errors="ignore") as f:
                code = f.read()

            loc = len(code.splitlines())

            # Python: AST-based analysis
            if language == "python":
                tree = ast.parse(code, filename=file_path)
                visitor = CodeAnalyzerVisitor(self.complexity_threshold)
                visitor.visit(tree)
                max_complex = max([fi.complexity for fi in visitor.functions] + [1])
                for c in visitor.classes:
                    for m in c.methods:
                        max_complex = max(max_complex, m.complexity)

                return FileAnalysisResult(
                    path=file_path,
                    language="python",
                    status="success",
                    lines_of_code=loc,
                    complexity_score=max_complex,
                    functions=visitor.functions,
                    classes=visitor.classes,
                    imports=visitor.imports,
                    complexity_warnings=visitor.complexity_warnings,
                )

            # JS/TS/Java: lightweight heuristics for v1.0 multi-language support
            imports: list[str] = []
            if language in ("javascript", "typescript"):
                # import x from 'y';  import {a} from "b";  require('x')
                import_re = re.compile(r"\bfrom\s+['\"]([^'\"]+)['\"]|\brequire\(\s*['\"]([^'\"]+)['\"]\s*\)")
                for m in import_re.finditer(code):
                    mod = m.group(1) or m.group(2)
                    if mod:
                        imports.append(mod)
            elif language == "java":
                for line in code.splitlines():
                    line_s = line.strip()
                    if line_s.startswith("import ") and line_s.endswith(";"):
                        imports.append(line_s[len("import ") : -1].strip())

            complexity = self._estimate_complexity_text(code, language)
            warnings: list[FunctionInfo] = []
            if complexity > self.complexity_threshold:
                warnings.append(FunctionInfo(name=path_obj.name, lineno=1, complexity=complexity))

            return FileAnalysisResult(
                path=file_path,
                language=language,
                status="success",
                lines_of_code=loc,
                complexity_score=complexity,
                functions=[],
                classes=[],
                imports=imports,
                complexity_warnings=warnings,
            )

        except SyntaxError as e:
            return FileAnalysisResult(
                path=file_path,
                language=self._detect_language(Path(file_path)),
                status="error",
                error=f"Syntax error at line {e.lineno}: {e.msg}",
            )
        except Exception as e:
            return FileAnalysisResult(
                path=file_path,
                language=self._detect_language(Path(file_path)),
                status="error",
                error=str(e),
            )

    def generate_report(self, result: CrawlResult | None = None, output_path: str | None = None) -> str:
        """
        Generate a Markdown report of the crawl results.

        Args:
            result: CrawlResult to report on (crawls if None)
            output_path: Optional path to write the report

        Returns:
            Markdown report string
        """
        if result is None:
            result = self.crawl()

        md_lines = [
            "# Project Python Analysis Report",
            "",
            f"**Target:** `{result.root_path}`",
            f"**Date:** {result.timestamp}",
            "",
            "## Executive Summary",
            "",
            f"- **Total Files Scanned:** {result.total_files}",
            f"- **Successful Analyses:** {len(result.files_analyzed)}",
            f"- **Failed Analyses:** {len(result.files_with_errors)}",
            f"- **Total Lines of Code:** {result.total_lines_of_code:,}",
            f"- **Total Functions:** {result.total_functions}",
            f"- **Total Classes:** {result.total_classes}",
            f"- **Complexity Hotspots:** {len(result.all_complexity_warnings)}",
            "",
            "---",
            "",
        ]

        # Complexity warnings section
        md_lines.append(f"## Complexity Warnings (Score > {self.complexity_threshold})")
        md_lines.append("")

        warnings = result.all_complexity_warnings
        if not warnings:
            md_lines.append("No overly complex functions detected.")
        else:
            md_lines.append("| File | Function | Complexity | Line |")
            md_lines.append("|------|----------|------------|------|")
            for file_path, func in sorted(warnings, key=lambda x: x[1].complexity, reverse=True):
                rel_path = os.path.relpath(file_path, result.root_path)
                md_lines.append(f"| `{rel_path}` | `{func.qualified_name}` | **{func.complexity}** | {func.lineno} |")
        md_lines.append("")

        # File statistics section
        md_lines.append("## File Statistics")
        md_lines.append("")
        md_lines.append("| File | LOC | Classes | Functions | Imports |")
        md_lines.append("|------|-----|---------|-----------|---------|")

        for file_result in sorted(result.files_analyzed, key=lambda x: x.lines_of_code, reverse=True):
            rel_path = os.path.relpath(file_result.path, result.root_path)
            md_lines.append(
                f"| `{rel_path}` | {file_result.lines_of_code} | "
                f"{len(file_result.classes)} | {file_result.total_functions} | "
                f"{len(file_result.imports)} |"
            )
        md_lines.append("")

        # Error section
        if result.files_with_errors:
            md_lines.append("## Analysis Errors")
            md_lines.append("")
            md_lines.append("| File | Error |")
            md_lines.append("|------|-------|")
            for file_result in result.files_with_errors:
                rel_path = os.path.relpath(file_result.path, result.root_path)
                error_msg = file_result.error or "Unknown error"
                md_lines.append(f"| `{rel_path}` | {error_msg} |")
            md_lines.append("")

        report = "\n".join(md_lines)

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report)

        return report

    def to_dict(self, result: CrawlResult | None = None) -> CrawlResultDict:
        """
        Convert crawl results to a dictionary for JSON serialization.

        Args:
            result: CrawlResult to convert (crawls if None)

        Returns:
            Dictionary representation of the results
        """
        if result is None:
            result = self.crawl()

        def file_result_to_dict(fr: FileAnalysisResult) -> dict[str, Any]:
            return {
                "path": os.path.relpath(fr.path, result.root_path),
                "status": fr.status,
                "lines_of_code": fr.lines_of_code,
                "functions": [
                    {
                        "name": f.qualified_name,
                        "lineno": f.lineno,
                        "complexity": f.complexity,
                    }
                    for f in fr.functions
                ],
                "classes": [
                    {
                        "name": c.name,
                        "lineno": c.lineno,
                        "methods": [
                            {
                                "name": m.name,
                                "lineno": m.lineno,
                                "complexity": m.complexity,
                            }
                            for m in c.methods
                        ],
                        "bases": c.bases,
                    }
                    for c in fr.classes
                ],
                "imports": fr.imports,
                "complexity_warnings": [
                    {
                        "name": f.qualified_name,
                        "lineno": f.lineno,
                        "complexity": f.complexity,
                    }
                    for f in fr.complexity_warnings
                ],
                "error": fr.error,
            }

        return {
            "root_path": result.root_path,
            "timestamp": result.timestamp,
            "summary": result.summary,
            "files": [file_result_to_dict(f) for f in result.files_analyzed],
            "errors": [file_result_to_dict(f) for f in result.files_with_errors],
        }


def crawl_project(
    root_path: str,
    exclude_dirs: list[str] | None = None,
    complexity_threshold: int = DEFAULT_COMPLEXITY_THRESHOLD,
) -> CrawlResultDict:
    """
    Convenience function to crawl a project and return results as a dictionary.

    Args:
        root_path: Path to the project root
        exclude_dirs: Optional list of directory names to exclude
        complexity_threshold: Complexity score that triggers a warning

    Returns:
        Dictionary with crawl results
    """
    exclude_set = frozenset(exclude_dirs) if exclude_dirs else None
    crawler = ProjectCrawler(
        root_path,
        exclude_dirs=exclude_set,
        complexity_threshold=complexity_threshold,
    )
    result = crawler.crawl()
    return crawler.to_dict(result)
