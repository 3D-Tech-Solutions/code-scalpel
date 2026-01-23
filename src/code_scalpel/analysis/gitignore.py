"""Simple .gitignore parser for file filtering.

Provides minimal but sufficient gitignore pattern matching for file crawling.
Does not support advanced features like negation patterns (!pattern).
"""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path


class GitignoreParser:
    """Simple gitignore pattern parser."""

    def __init__(self, patterns: list[str]):
        """Initialize with gitignore patterns.

        Args:
            patterns: List of gitignore patterns (without comments or empty lines)
        """
        self.patterns = patterns

    @classmethod
    def from_file(cls, gitignore_path: str) -> GitignoreParser:
        """Load patterns from a .gitignore file.

        Args:
            gitignore_path: Path to .gitignore file

        Returns:
            GitignoreParser instance
        """
        patterns: list[str] = []
        try:
            path = Path(gitignore_path)
            if path.exists() and path.is_file():
                for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                    line = raw.strip()
                    # Skip empty lines and comments
                    if not line or line.startswith("#"):
                        continue
                    # Skip negation patterns (not supported)
                    if line.startswith("!"):
                        continue
                    patterns.append(line)
        except Exception:
            # If we can't read the file, just use no patterns
            pass

        return cls(patterns)

    def _matches_pattern(self, rel_posix_path: str, pattern: str, *, is_dir: bool) -> bool:
        """Check if a path matches a gitignore pattern.

        Args:
            rel_posix_path: Path relative to repo root, in POSIX format
            pattern: Gitignore pattern
            is_dir: Whether the path is a directory

        Returns:
            True if pattern matches the path
        """
        # Directory-only patterns
        if pattern.endswith("/"):
            if not is_dir:
                return False
            pattern = pattern[:-1]

        # Path patterns (contain /)
        if "/" in pattern:
            return fnmatch(rel_posix_path, pattern)

        # Simple filename patterns (no /)
        return fnmatch(Path(rel_posix_path).name, pattern)

    def is_ignored(self, rel_path: Path | str, *, is_dir: bool = False) -> bool:
        """Check if a path should be ignored.

        Args:
            rel_path: Path relative to repo root
            is_dir: Whether this is a directory

        Returns:
            True if path matches any gitignore pattern
        """
        if not self.patterns:
            return False

        if isinstance(rel_path, str):
            rel_path = Path(rel_path)

        rel_posix = rel_path.as_posix().lstrip("./")
        return any(self._matches_pattern(rel_posix, pat, is_dir=is_dir) for pat in self.patterns)
