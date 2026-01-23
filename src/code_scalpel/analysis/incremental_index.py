"""
Incremental Indexing - Cache analysis results for massive codebases.

[20251226_FEATURE] Enterprise tier feature for crawl_project.

Uses SQLite to track file hashes and cached analysis results:
- Only re-parses changed files
- Persists analysis between runs
- Supports 100k+ file projects efficiently

Usage:
    from code_scalpel.analysis.incremental_index import IncrementalIndex

    index = IncrementalIndex("/path/to/project")

    # Check if file needs re-analysis
    if index.needs_reanalysis("src/main.py"):
        result = analyze_file("src/main.py")
        index.store_analysis("src/main.py", result)
    else:
        result = index.get_cached_analysis("src/main.py")
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CachedFileAnalysis:
    """Cached analysis result for a file."""

    path: str
    content_hash: str
    analysis_timestamp: float
    lines_of_code: int
    functions: list[dict[str, Any]]
    classes: list[dict[str, Any]]
    imports: list[str]
    complexity_warnings: list[dict[str, Any]]
    error: str | None = None


@dataclass
class IndexStats:
    """Statistics about the incremental index."""

    total_files: int
    cached_files: int
    stale_files: int  # Files that need re-analysis
    cache_hit_rate: float
    last_full_crawl: float | None
    database_size_bytes: int


class IncrementalIndex:
    """SQLite-based incremental index for file analysis caching."""

    SCHEMA_VERSION = 1

    def __init__(
        self,
        project_root: str | Path,
        cache_dir: str | Path | None = None,
        database_name: str = ".scalpel_index.db",
    ):
        """
        Initialize incremental index.

        Args:
            project_root: Root directory of the project
            cache_dir: Directory for cache database (defaults to project root)
            database_name: Name of the SQLite database file
        """
        self.root = Path(project_root)
        self.cache_dir = Path(cache_dir) if cache_dir else self.root
        self.db_path = self.cache_dir / database_name
        self._connection: sqlite3.Connection | None = None

        # Initialize database
        self._init_database()

    def _init_database(self) -> None:
        """Create database schema if not exists."""
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY
                );

                CREATE TABLE IF NOT EXISTS file_analysis (
                    path TEXT PRIMARY KEY,
                    content_hash TEXT NOT NULL,
                    analysis_timestamp REAL NOT NULL,
                    lines_of_code INTEGER DEFAULT 0,
                    functions_json TEXT,
                    classes_json TEXT,
                    imports_json TEXT,
                    complexity_warnings_json TEXT,
                    error TEXT
                );

                CREATE TABLE IF NOT EXISTS crawl_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_content_hash ON file_analysis(content_hash);
                CREATE INDEX IF NOT EXISTS idx_timestamp ON file_analysis(analysis_timestamp);
            """)

            # Check/set schema version
            cursor = conn.execute("SELECT version FROM schema_version LIMIT 1")
            row = cursor.fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO schema_version (version) VALUES (?)",
                    (self.SCHEMA_VERSION,),
                )
            elif row[0] != self.SCHEMA_VERSION:
                # Handle schema migration if needed
                self._migrate_schema(conn, row[0], self.SCHEMA_VERSION)

    def _migrate_schema(self, conn: sqlite3.Connection, from_ver: int, to_ver: int) -> None:
        """Migrate database schema between versions."""
        # For now, just update the version - add migrations as needed
        conn.execute("UPDATE schema_version SET version = ?", (to_ver,))

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a database connection with proper lifecycle management."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def compute_file_hash(self, file_path: str | Path) -> str:
        """Compute content hash for a file."""
        full_path = self.root / file_path if not Path(file_path).is_absolute() else Path(file_path)

        hasher = hashlib.sha256()
        try:
            with open(full_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""

    def needs_reanalysis(self, file_path: str) -> bool:
        """Check if a file needs re-analysis based on content hash."""
        current_hash = self.compute_file_hash(file_path)
        if not current_hash:
            return True  # File doesn't exist or can't be read

        with self._get_connection() as conn:
            cursor = conn.execute("SELECT content_hash FROM file_analysis WHERE path = ?", (file_path,))
            row = cursor.fetchone()

            if row is None:
                return True  # Not in cache
            return row["content_hash"] != current_hash

    def get_cached_analysis(self, file_path: str) -> CachedFileAnalysis | None:
        """Get cached analysis for a file if available and valid."""
        if self.needs_reanalysis(file_path):
            return None

        with self._get_connection() as conn:
            cursor = conn.execute(
                """SELECT path, content_hash, analysis_timestamp, lines_of_code,
                          functions_json, classes_json, imports_json,
                          complexity_warnings_json, error
                   FROM file_analysis WHERE path = ?""",
                (file_path,),
            )
            row = cursor.fetchone()

            if row is None:
                return None

            return CachedFileAnalysis(
                path=row["path"],
                content_hash=row["content_hash"],
                analysis_timestamp=row["analysis_timestamp"],
                lines_of_code=row["lines_of_code"],
                functions=json.loads(row["functions_json"] or "[]"),
                classes=json.loads(row["classes_json"] or "[]"),
                imports=json.loads(row["imports_json"] or "[]"),
                complexity_warnings=json.loads(row["complexity_warnings_json"] or "[]"),
                error=row["error"],
            )

    def store_analysis(
        self,
        file_path: str,
        lines_of_code: int,
        functions: list[dict[str, Any]],
        classes: list[dict[str, Any]],
        imports: list[str],
        complexity_warnings: list[dict[str, Any]],
        error: str | None = None,
    ) -> None:
        """Store analysis result for a file."""
        content_hash = self.compute_file_hash(file_path)

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO file_analysis
                (path, content_hash, analysis_timestamp, lines_of_code,
                 functions_json, classes_json, imports_json,
                 complexity_warnings_json, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    file_path,
                    content_hash,
                    time.time(),
                    lines_of_code,
                    json.dumps(functions),
                    json.dumps(classes),
                    json.dumps(imports),
                    json.dumps(complexity_warnings),
                    error,
                ),
            )

    def get_all_cached_paths(self) -> list[str]:
        """Get all file paths in the cache."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT path FROM file_analysis")
            return [row["path"] for row in cursor.fetchall()]

    def get_stale_files(self) -> list[str]:
        """Get list of files that need re-analysis."""
        cached_paths = self.get_all_cached_paths()
        return [p for p in cached_paths if self.needs_reanalysis(p)]

    def invalidate(self, file_path: str) -> None:
        """Invalidate cache for a specific file."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM file_analysis WHERE path = ?", (file_path,))

    def invalidate_all(self) -> None:
        """Clear all cached analysis."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM file_analysis")

    def get_stats(self) -> IndexStats:
        """Get statistics about the index."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM file_analysis")
            total_cached = cursor.fetchone()[0]

            cursor = conn.execute("SELECT value FROM crawl_metadata WHERE key = 'last_full_crawl'")
            row = cursor.fetchone()
            last_crawl = float(row["value"]) if row else None

        stale_files = self.get_stale_files()
        stale_count = len(stale_files)

        # Calculate cache hit rate
        hit_rate = 1.0 - (stale_count / max(total_cached, 1))

        # Get database size
        db_size = self.db_path.stat().st_size if self.db_path.exists() else 0

        return IndexStats(
            total_files=total_cached + stale_count,
            cached_files=total_cached,
            stale_files=stale_count,
            cache_hit_rate=hit_rate,
            last_full_crawl=last_crawl,
            database_size_bytes=db_size,
        )

    def set_metadata(self, key: str, value: str) -> None:
        """Store metadata about the crawl."""
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO crawl_metadata (key, value) VALUES (?, ?)",
                (key, value),
            )

    def get_metadata(self, key: str) -> str | None:
        """Get stored metadata."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT value FROM crawl_metadata WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else None
