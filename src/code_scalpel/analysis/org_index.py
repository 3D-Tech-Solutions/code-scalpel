"""
Organization Index - Centralized indexing for organization-wide code search.

[20251226_FEATURE] Enterprise tier feature for crawl_project.

Features:
- Elasticsearch/OpenSearch integration for full-text search
- Symbol index for cross-project navigation
- Federated search across multiple repositories
- Incremental updates with change detection

Usage:
    from code_scalpel.analysis.org_index import OrganizationIndex

    index = OrganizationIndex("http://localhost:9200")
    index.add_project("/path/to/repo", "my-repo")

    results = index.search("authenticate user", limit=10)
"""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class IndexedFile:
    """A file indexed in the organization index."""

    repo_name: str
    file_path: str
    content_hash: str
    language: str
    symbols: list[str]
    imports: list[str]
    indexed_at: str
    line_count: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class IndexedSymbol:
    """A symbol (function, class, etc.) indexed for cross-project search."""

    name: str
    symbol_type: str  # "function", "class", "method", "constant"
    repo_name: str
    file_path: str
    line_number: int
    signature: str | None = None
    docstring: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """A search result from the organization index."""

    repo_name: str
    file_path: str
    line_number: int | None
    content_snippet: str
    score: float
    symbol_name: str | None = None
    match_type: str = "content"  # "content", "symbol", "file_name"


@dataclass
class IndexStats:
    """Statistics about the organization index."""

    total_repos: int
    total_files: int
    total_symbols: int
    total_lines: int
    last_updated: str
    repos: dict[str, int]  # repo -> file count


class SearchBackend(ABC):
    """Abstract interface for search backends."""

    @abstractmethod
    def index_file(self, file: IndexedFile) -> bool:
        """Index a file."""
        pass

    @abstractmethod
    def index_symbol(self, symbol: IndexedSymbol) -> bool:
        """Index a symbol."""
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        repos: list[str] | None = None,
        languages: list[str] | None = None,
        limit: int = 20,
    ) -> list[SearchResult]:
        """Search the index."""
        pass

    @abstractmethod
    def search_symbols(
        self,
        query: str,
        symbol_type: str | None = None,
        limit: int = 20,
    ) -> list[IndexedSymbol]:
        """Search for symbols by name."""
        pass

    @abstractmethod
    def delete_repo(self, repo_name: str) -> int:
        """Delete all entries for a repository. Returns count deleted."""
        pass

    @abstractmethod
    def get_stats(self) -> IndexStats:
        """Get index statistics."""
        pass


class InMemoryBackend(SearchBackend):
    """In-memory search backend for testing and small deployments."""

    def __init__(self):
        """Initialize in-memory storage."""
        self._files: dict[str, IndexedFile] = {}  # key = repo:path
        self._symbols: dict[str, IndexedSymbol] = {}  # key = repo:path:name

    def index_file(self, file: IndexedFile) -> bool:
        """Index a file."""
        key = f"{file.repo_name}:{file.file_path}"
        self._files[key] = file
        return True

    def index_symbol(self, symbol: IndexedSymbol) -> bool:
        """Index a symbol."""
        key = f"{symbol.repo_name}:{symbol.file_path}:{symbol.name}"
        self._symbols[key] = symbol
        return True

    def search(
        self,
        query: str,
        repos: list[str] | None = None,
        languages: list[str] | None = None,
        limit: int = 20,
    ) -> list[SearchResult]:
        """Search the index using simple string matching."""
        results: list[SearchResult] = []
        query_lower = query.lower()

        for file in self._files.values():
            # Filter by repo
            if repos and file.repo_name not in repos:
                continue
            # Filter by language
            if languages and file.language not in languages:
                continue

            # Check file name match
            if query_lower in file.file_path.lower():
                results.append(
                    SearchResult(
                        repo_name=file.repo_name,
                        file_path=file.file_path,
                        line_number=None,
                        content_snippet=file.file_path,
                        score=1.0,
                        match_type="file_name",
                    )
                )

            # Check symbol match
            for symbol_name in file.symbols:
                if query_lower in symbol_name.lower():
                    results.append(
                        SearchResult(
                            repo_name=file.repo_name,
                            file_path=file.file_path,
                            line_number=None,
                            content_snippet=f"Symbol: {symbol_name}",
                            score=0.8,
                            symbol_name=symbol_name,
                            match_type="symbol",
                        )
                    )

        # Sort by score and limit
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def search_symbols(
        self,
        query: str,
        symbol_type: str | None = None,
        limit: int = 20,
    ) -> list[IndexedSymbol]:
        """Search for symbols by name."""
        results: list[IndexedSymbol] = []
        query_lower = query.lower()

        for symbol in self._symbols.values():
            if symbol_type and symbol.symbol_type != symbol_type:
                continue
            if query_lower in symbol.name.lower():
                results.append(symbol)

        return results[:limit]

    def delete_repo(self, repo_name: str) -> int:
        """Delete all entries for a repository."""
        count = 0

        # Delete files
        keys_to_delete = [k for k in self._files if k.startswith(f"{repo_name}:")]
        for key in keys_to_delete:
            del self._files[key]
            count += 1

        # Delete symbols
        keys_to_delete = [k for k in self._symbols if k.startswith(f"{repo_name}:")]
        for key in keys_to_delete:
            del self._symbols[key]
            count += 1

        return count

    def get_stats(self) -> IndexStats:
        """Get index statistics."""
        repos: dict[str, int] = {}
        total_lines = 0

        for file in self._files.values():
            if file.repo_name not in repos:
                repos[file.repo_name] = 0
            repos[file.repo_name] += 1
            total_lines += file.line_count

        return IndexStats(
            total_repos=len(repos),
            total_files=len(self._files),
            total_symbols=len(self._symbols),
            total_lines=total_lines,
            last_updated=datetime.now().isoformat(),
            repos=repos,
        )


class ElasticsearchBackend(SearchBackend):
    """Elasticsearch/OpenSearch backend for production deployments."""

    def __init__(
        self,
        host: str = "http://localhost:9200",
        index_prefix: str = "code_scalpel_",
        username: str | None = None,
        password: str | None = None,
    ):
        """
        Initialize Elasticsearch backend.

        Args:
            host: Elasticsearch host URL
            index_prefix: Prefix for index names
            username: Optional username for authentication
            password: Optional password for authentication
        """
        self.host = host.rstrip("/")
        self.index_prefix = index_prefix
        self.auth = (username, password) if username and password else None

        # Index names
        self.files_index = f"{index_prefix}files"
        self.symbols_index = f"{index_prefix}symbols"

    def _request(
        self,
        method: str,
        path: str,
        body: dict | None = None,
    ) -> dict[str, Any]:
        """Make HTTP request to Elasticsearch."""
        import urllib.error
        import urllib.parse
        import urllib.request

        url = f"{self.host}/{path}"
        parsed = urllib.parse.urlparse(url)
        # [20260102_BUGFIX] Enforce network URL schemes to block file:// access.
        if parsed.scheme not in {"http", "https"}:
            raise ValueError(f"Unsupported URL scheme for Elasticsearch host: {parsed.scheme}")
        headers = {"Content-Type": "application/json"}

        data = json.dumps(body).encode() if body else None

        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        if self.auth:
            import base64

            credentials = base64.b64encode(f"{self.auth[0]}:{self.auth[1]}".encode()).decode()
            req.add_header("Authorization", f"Basic {credentials}")

        try:
            with urllib.request.urlopen(req, timeout=30) as response:  # nosec B310
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"found": False}
            raise

    def _ensure_indices(self) -> None:
        """Create indices if they don't exist."""
        # Files index mapping
        files_mapping = {
            "mappings": {
                "properties": {
                    "repo_name": {"type": "keyword"},
                    "file_path": {"type": "keyword"},
                    "content_hash": {"type": "keyword"},
                    "language": {"type": "keyword"},
                    "symbols": {"type": "keyword"},
                    "imports": {"type": "keyword"},
                    "indexed_at": {"type": "date"},
                    "line_count": {"type": "integer"},
                }
            }
        }

        # Symbols index mapping
        symbols_mapping = {
            "mappings": {
                "properties": {
                    "name": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "symbol_type": {"type": "keyword"},
                    "repo_name": {"type": "keyword"},
                    "file_path": {"type": "keyword"},
                    "line_number": {"type": "integer"},
                    "signature": {"type": "text"},
                    "docstring": {"type": "text"},
                }
            }
        }

        try:
            self._request("PUT", self.files_index, files_mapping)
        except Exception:
            pass  # Index may already exist

        try:
            self._request("PUT", self.symbols_index, symbols_mapping)
        except Exception:
            pass

    def index_file(self, file: IndexedFile) -> bool:
        """Index a file in Elasticsearch."""
        self._ensure_indices()

        doc_id = hashlib.sha256(f"{file.repo_name}:{file.file_path}".encode()).hexdigest()

        doc = {
            "repo_name": file.repo_name,
            "file_path": file.file_path,
            "content_hash": file.content_hash,
            "language": file.language,
            "symbols": file.symbols,
            "imports": file.imports,
            "indexed_at": file.indexed_at,
            "line_count": file.line_count,
        }

        try:
            self._request("PUT", f"{self.files_index}/_doc/{doc_id}", doc)
            return True
        except Exception:
            return False

    def index_symbol(self, symbol: IndexedSymbol) -> bool:
        """Index a symbol in Elasticsearch."""
        self._ensure_indices()

        doc_id = hashlib.sha256(
            f"{symbol.repo_name}:{symbol.file_path}:{symbol.name}:{symbol.line_number}".encode()
        ).hexdigest()

        doc = {
            "name": symbol.name,
            "symbol_type": symbol.symbol_type,
            "repo_name": symbol.repo_name,
            "file_path": symbol.file_path,
            "line_number": symbol.line_number,
            "signature": symbol.signature,
            "docstring": symbol.docstring,
        }

        try:
            self._request("PUT", f"{self.symbols_index}/_doc/{doc_id}", doc)
            return True
        except Exception:
            return False

    def search(
        self,
        query: str,
        repos: list[str] | None = None,
        languages: list[str] | None = None,
        limit: int = 20,
    ) -> list[SearchResult]:
        """Search the index using Elasticsearch."""
        must_clauses = [{"multi_match": {"query": query, "fields": ["file_path", "symbols"]}}]

        if repos:
            must_clauses.append({"terms": {"repo_name": repos}})
        if languages:
            must_clauses.append({"terms": {"language": languages}})

        search_body = {
            "query": {"bool": {"must": must_clauses}},
            "size": limit,
        }

        try:
            response = self._request("POST", f"{self.files_index}/_search", search_body)

            results: list[SearchResult] = []
            for hit in response.get("hits", {}).get("hits", []):
                source = hit["_source"]
                results.append(
                    SearchResult(
                        repo_name=source["repo_name"],
                        file_path=source["file_path"],
                        line_number=None,
                        content_snippet=source["file_path"],
                        score=hit["_score"],
                        match_type="content",
                    )
                )

            return results
        except Exception:
            return []

    def search_symbols(
        self,
        query: str,
        symbol_type: str | None = None,
        limit: int = 20,
    ) -> list[IndexedSymbol]:
        """Search for symbols by name."""
        must_clauses = [{"match": {"name": query}}]

        if symbol_type:
            must_clauses.append({"term": {"symbol_type": symbol_type}})

        search_body = {
            "query": {"bool": {"must": must_clauses}},
            "size": limit,
        }

        try:
            response = self._request("POST", f"{self.symbols_index}/_search", search_body)

            results: list[IndexedSymbol] = []
            for hit in response.get("hits", {}).get("hits", []):
                source = hit["_source"]
                results.append(
                    IndexedSymbol(
                        name=source["name"],
                        symbol_type=source["symbol_type"],
                        repo_name=source["repo_name"],
                        file_path=source["file_path"],
                        line_number=source["line_number"],
                        signature=source.get("signature"),
                        docstring=source.get("docstring"),
                    )
                )

            return results
        except Exception:
            return []

    def delete_repo(self, repo_name: str) -> int:
        """Delete all entries for a repository."""
        delete_query = {"query": {"term": {"repo_name": repo_name}}}

        count = 0
        try:
            response = self._request(
                "POST",
                f"{self.files_index}/_delete_by_query",
                delete_query,
            )
            count += response.get("deleted", 0)
        except Exception:
            pass

        try:
            response = self._request(
                "POST",
                f"{self.symbols_index}/_delete_by_query",
                delete_query,
            )
            count += response.get("deleted", 0)
        except Exception:
            pass

        return count

    def get_stats(self) -> IndexStats:
        """Get index statistics."""
        stats = IndexStats(
            total_repos=0,
            total_files=0,
            total_symbols=0,
            total_lines=0,
            last_updated=datetime.now().isoformat(),
            repos={},
        )

        try:
            # Get file count
            response = self._request("GET", f"{self.files_index}/_count")
            stats.total_files = response.get("count", 0)

            # Get symbol count
            response = self._request("GET", f"{self.symbols_index}/_count")
            stats.total_symbols = response.get("count", 0)

            # Get repo aggregation
            agg_query = {
                "size": 0,
                "aggs": {"repos": {"terms": {"field": "repo_name", "size": 1000}}},
            }
            response = self._request("POST", f"{self.files_index}/_search", agg_query)

            for bucket in response.get("aggregations", {}).get("repos", {}).get("buckets", []):
                stats.repos[bucket["key"]] = bucket["doc_count"]

            stats.total_repos = len(stats.repos)

        except Exception:
            pass

        return stats


class OrganizationIndex:
    """High-level interface for organization-wide code indexing."""

    LANGUAGE_EXTENSIONS = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".rb": "ruby",
        ".php": "php",
    }

    def __init__(
        self,
        backend: SearchBackend | None = None,
        elasticsearch_host: str | None = None,
    ):
        """
        Initialize organization index.

        Args:
            backend: Custom search backend
            elasticsearch_host: If provided, use Elasticsearch backend
        """
        if backend:
            self._backend = backend
        elif elasticsearch_host:
            self._backend = ElasticsearchBackend(host=elasticsearch_host)
        else:
            self._backend = InMemoryBackend()

    def add_project(
        self,
        project_path: str | Path,
        repo_name: str | None = None,
        exclude_dirs: set[str] | None = None,
    ) -> int:
        """
        Add a project to the organization index.

        Args:
            project_path: Path to the project
            repo_name: Repository name (defaults to directory name)
            exclude_dirs: Directories to exclude

        Returns:
            Number of files indexed
        """
        root = Path(project_path).resolve()
        name = repo_name or root.name
        exclude = exclude_dirs or {
            "node_modules",
            ".git",
            "__pycache__",
            ".venv",
            "venv",
        }

        indexed_count = 0

        for ext, lang in self.LANGUAGE_EXTENSIONS.items():
            for file_path in root.rglob(f"*{ext}"):
                if any(ex in file_path.parts for ex in exclude):
                    continue

                try:
                    indexed_file = self._index_file(file_path, name, lang, root)
                    if indexed_file:
                        self._backend.index_file(indexed_file)
                        indexed_count += 1
                except Exception:
                    pass

        return indexed_count

    def _index_file(
        self,
        file_path: Path,
        repo_name: str,
        language: str,
        root: Path,
    ) -> IndexedFile | None:
        """Index a single file."""
        try:
            content = file_path.read_text(errors="replace")
        except Exception:
            return None

        # Compute hash
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        # Extract symbols
        symbols: list[str] = []
        imports: list[str] = []

        if language == "python":
            symbols, imports = self._extract_python_info(content)
        elif language in ("javascript", "typescript"):
            symbols, imports = self._extract_js_info(content)

        rel_path = str(file_path.relative_to(root))

        indexed_file = IndexedFile(
            repo_name=repo_name,
            file_path=rel_path,
            content_hash=content_hash,
            language=language,
            symbols=symbols,
            imports=imports,
            indexed_at=datetime.now().isoformat(),
            line_count=len(content.splitlines()),
        )

        # Index individual symbols
        for symbol in symbols:
            self._backend.index_symbol(
                IndexedSymbol(
                    name=symbol,
                    symbol_type="function",  # Simplified
                    repo_name=repo_name,
                    file_path=rel_path,
                    line_number=0,  # Would need AST for accurate line numbers
                )
            )

        return indexed_file

    def _extract_python_info(self, content: str) -> tuple[list[str], list[str]]:
        """Extract symbols and imports from Python code."""
        import ast

        symbols: list[str] = []
        imports: list[str] = []

        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append(node.name)
                elif isinstance(node, ast.ClassDef):
                    symbols.append(node.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
        except SyntaxError:
            pass

        return symbols, imports

    def _extract_js_info(self, content: str) -> tuple[list[str], list[str]]:
        """Extract symbols and imports from JavaScript/TypeScript code."""
        import re

        symbols: list[str] = []
        imports: list[str] = []

        # Functions
        for match in re.finditer(r"function\s+(\w+)", content):
            symbols.append(match.group(1))

        # Arrow functions assigned to const/let/var
        for match in re.finditer(r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(", content):
            symbols.append(match.group(1))

        # Classes
        for match in re.finditer(r"class\s+(\w+)", content):
            symbols.append(match.group(1))

        # Imports
        for match in re.finditer(r"import\s+.*from\s+['\"]([^'\"]+)['\"]", content):
            imports.append(match.group(1))
        for match in re.finditer(r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", content):
            imports.append(match.group(1))

        return symbols, imports

    def search(
        self,
        query: str,
        repos: list[str] | None = None,
        languages: list[str] | None = None,
        limit: int = 20,
    ) -> list[SearchResult]:
        """
        Search across all indexed repositories.

        Args:
            query: Search query
            repos: Filter to specific repositories
            languages: Filter to specific languages
            limit: Maximum results

        Returns:
            List of search results
        """
        return self._backend.search(query, repos, languages, limit)

    def search_symbols(
        self,
        query: str,
        symbol_type: str | None = None,
        limit: int = 20,
    ) -> list[IndexedSymbol]:
        """
        Search for symbols by name.

        Args:
            query: Symbol name to search for
            symbol_type: Filter to specific type (function, class, etc.)
            limit: Maximum results

        Returns:
            List of matching symbols
        """
        return self._backend.search_symbols(query, symbol_type, limit)

    def remove_project(self, repo_name: str) -> int:
        """
        Remove a project from the index.

        Args:
            repo_name: Repository name to remove

        Returns:
            Number of entries removed
        """
        return self._backend.delete_repo(repo_name)

    def get_stats(self) -> IndexStats:
        """Get index statistics."""
        return self._backend.get_stats()


def create_org_index(
    elasticsearch_host: str | None = None,
) -> OrganizationIndex:
    """
    Create an organization index.

    Args:
        elasticsearch_host: Optional Elasticsearch host URL

    Returns:
        OrganizationIndex instance
    """
    return OrganizationIndex(elasticsearch_host=elasticsearch_host)
