"""
Parallel Crawler - High-performance crawling for 100k+ file repositories.

[20251226_FEATURE] Enterprise tier feature for crawl_project.

Features:
- Multi-threaded file discovery
- Chunked analysis with progress reporting
- Memory-efficient streaming processing
- Automatic worker scaling based on CPU cores
- Incremental results for progress tracking

Usage:
    from code_scalpel.analysis.parallel_crawler import ParallelCrawler

    crawler = ParallelCrawler("/path/to/large/repo", max_workers=8)
    for chunk_result in crawler.crawl_chunked(chunk_size=1000):
        print(f"Processed {chunk_result.files_processed} files")
"""

from __future__ import annotations

import hashlib
import os
import time
from collections.abc import Callable, Generator
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .gitignore import GitignoreParser


@dataclass
class FileInfo:
    """Information about a discovered file."""

    path: str
    size: int
    mtime: float
    content_hash: str | None = None


@dataclass
class CrawlChunk:
    """A chunk of crawled files with analysis results."""

    chunk_id: int
    files: list[FileInfo]
    files_processed: int
    total_discovered: int
    elapsed_seconds: float
    analysis_results: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParallelCrawlResult:
    """Final result of parallel crawl."""

    total_files: int
    total_size_bytes: int
    files_analyzed: int
    elapsed_seconds: float
    chunks_processed: int
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class ParallelCrawler:
    """High-performance parallel file crawler for large repositories."""

    # Default exclude patterns for performance
    DEFAULT_EXCLUDES = {
        "node_modules",
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        "dist",
        "build",
        ".next",
        ".nuxt",
        "target",  # Rust/Java
        ".gradle",
        ".idea",
        ".vscode",
        "coverage",
        "htmlcov",
        ".eggs",
        "*.egg-info",
    }

    # Supported file extensions for analysis
    ANALYZABLE_EXTENSIONS = {
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".java",
        ".go",
        ".rs",
        ".rb",
        ".php",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".cs",
        ".swift",
        ".kt",
        ".scala",
        ".vue",
        ".svelte",
    }

    def __init__(
        self,
        project_root: str | Path,
        max_workers: int | None = None,
        exclude_patterns: set[str] | None = None,
        respect_gitignore: bool = True,
        max_file_size_mb: float = 10.0,
    ):
        """
        Initialize parallel crawler.

        Args:
            project_root: Root directory to crawl
            max_workers: Maximum worker threads (default: CPU cores * 2)
            exclude_patterns: Additional patterns to exclude
            respect_gitignore: Whether to respect .gitignore files
            max_file_size_mb: Maximum file size to analyze in MB
        """
        self.root = Path(project_root).resolve()
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) * 2)
        self.exclude_patterns = self.DEFAULT_EXCLUDES | (exclude_patterns or set())
        self.respect_gitignore = respect_gitignore
        self.max_file_size = int(max_file_size_mb * 1024 * 1024)

        # Initialize gitignore parser if needed
        self.gitignore: GitignoreParser | None = None
        if respect_gitignore:
            gitignore_path = self.root / ".gitignore"
            if gitignore_path.exists():
                self.gitignore = GitignoreParser.from_file(str(gitignore_path))

        # Statistics
        self._files_discovered = 0
        self._files_analyzed = 0
        self._total_size = 0
        self._errors: list[str] = []

    def discover_files(
        self,
        extensions: set[str] | None = None,
    ) -> Generator[FileInfo, None, None]:
        """
        Discover all files in the repository.

        Args:
            extensions: File extensions to include (default: all analyzable)

        Yields:
            FileInfo for each discovered file
        """
        target_extensions = extensions or self.ANALYZABLE_EXTENSIONS

        def should_skip_dir(dir_path: Path) -> bool:
            """Check if directory should be skipped."""
            dir_name = dir_path.name

            # Check explicit excludes
            if dir_name in self.exclude_patterns:
                return True

            # Check gitignore
            if self.gitignore:
                rel_path = str(dir_path.relative_to(self.root))
                if self.gitignore.is_ignored(rel_path):
                    return True

            return False

        def scan_directory(dir_path: Path) -> list[FileInfo]:
            """Scan a single directory."""
            files: list[FileInfo] = []

            try:
                for entry in os.scandir(dir_path):
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            continue  # Directories handled separately
                        if entry.is_file(follow_symlinks=False):
                            path = Path(entry.path)
                            if path.suffix.lower() in target_extensions:
                                stat = entry.stat()
                                if stat.st_size <= self.max_file_size:
                                    files.append(
                                        FileInfo(
                                            path=entry.path,
                                            size=stat.st_size,
                                            mtime=stat.st_mtime,
                                        )
                                    )
                    except (PermissionError, OSError):
                        pass
            except (PermissionError, OSError):
                pass

            return files

        # Walk directory tree
        dirs_to_scan = [self.root]

        while dirs_to_scan:
            current_dir = dirs_to_scan.pop()

            # Discover files in current directory
            for file_info in scan_directory(current_dir):
                self._files_discovered += 1
                self._total_size += file_info.size
                yield file_info

            # Add subdirectories
            try:
                for entry in os.scandir(current_dir):
                    if entry.is_dir(follow_symlinks=False):
                        subdir = Path(entry.path)
                        if not should_skip_dir(subdir):
                            dirs_to_scan.append(subdir)
            except (PermissionError, OSError):
                pass

    def crawl_chunked(
        self,
        chunk_size: int = 1000,
        analyzer: Callable[[Path], dict[str, Any]] | None = None,
    ) -> Generator[CrawlChunk, None, None]:
        """
        Crawl repository in chunks with parallel analysis.

        Args:
            chunk_size: Number of files per chunk
            analyzer: Optional function to analyze each file

        Yields:
            CrawlChunk with results for each chunk
        """
        start_time = time.time()
        chunk_id = 0
        current_chunk: list[FileInfo] = []

        for file_info in self.discover_files():
            current_chunk.append(file_info)

            if len(current_chunk) >= chunk_size:
                chunk_result = self._process_chunk(
                    chunk_id,
                    current_chunk,
                    analyzer,
                    start_time,
                )
                yield chunk_result
                chunk_id += 1
                current_chunk = []

        # Process remaining files
        if current_chunk:
            chunk_result = self._process_chunk(
                chunk_id,
                current_chunk,
                analyzer,
                start_time,
            )
            yield chunk_result

    def _process_chunk(
        self,
        chunk_id: int,
        files: list[FileInfo],
        analyzer: Callable[[Path], dict[str, Any]] | None,
        start_time: float,
    ) -> CrawlChunk:
        """Process a chunk of files in parallel."""
        analysis_results: dict[str, Any] = {}

        if analyzer:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_file = {executor.submit(self._safe_analyze, Path(f.path), analyzer): f for f in files}

                for future in as_completed(future_to_file):
                    file_info = future_to_file[future]
                    try:
                        result = future.result()
                        if result:
                            analysis_results[file_info.path] = result
                            self._files_analyzed += 1
                    except Exception as e:
                        self._errors.append(f"{file_info.path}: {e}")
        else:
            # Just count files
            self._files_analyzed += len(files)

        return CrawlChunk(
            chunk_id=chunk_id,
            files=files,
            files_processed=len(files),
            total_discovered=self._files_discovered,
            elapsed_seconds=time.time() - start_time,
            analysis_results=analysis_results,
        )

    def _safe_analyze(
        self,
        file_path: Path,
        analyzer: Callable[[Path], dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Safely analyze a file, catching exceptions."""
        try:
            return analyzer(file_path)
        except Exception as e:
            self._errors.append(f"{file_path}: {e}")
            return None

    def crawl_all(
        self,
        analyzer: Callable[[Path], dict[str, Any]] | None = None,
    ) -> ParallelCrawlResult:
        """
        Crawl entire repository and return final result.

        Args:
            analyzer: Optional function to analyze each file

        Returns:
            ParallelCrawlResult with complete statistics
        """
        start_time = time.time()
        chunks_processed = 0

        for _chunk in self.crawl_chunked(chunk_size=1000, analyzer=analyzer):
            chunks_processed += 1

        return ParallelCrawlResult(
            total_files=self._files_discovered,
            total_size_bytes=self._total_size,
            files_analyzed=self._files_analyzed,
            elapsed_seconds=time.time() - start_time,
            chunks_processed=chunks_processed,
            errors=self._errors,
            metadata={
                "max_workers": self.max_workers,
                "max_file_size_mb": self.max_file_size / (1024 * 1024),
            },
        )

    def compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file content."""
        hasher = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""


def parallel_crawl(
    project_root: str | Path,
    max_workers: int | None = None,
    chunk_size: int = 1000,
) -> Generator[CrawlChunk, None, None]:
    """
    Convenience function for parallel crawling.

    Args:
        project_root: Root directory to crawl
        max_workers: Maximum worker threads
        chunk_size: Files per chunk

    Yields:
        CrawlChunk for each processed chunk
    """
    crawler = ParallelCrawler(project_root, max_workers=max_workers)
    yield from crawler.crawl_chunked(chunk_size=chunk_size)
