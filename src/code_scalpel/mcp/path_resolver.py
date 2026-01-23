"""
Path Resolution Module for Docker and Multi-Environment Deployments.

[20251214_FEATURE] v1.5.3 - Intelligent path resolution for Docker deployments.
[20251215_FEATURE] v2.0.0 - Added Windows path resolution support.

This module provides intelligent path resolution that works seamlessly across:
- Local development environments
- Docker containers with volume mounts
- Remote MCP servers
- Various workspace configurations
- Windows paths (drive letters, UNC paths)
- WSL mount points (/mnt/c/, etc.)
- Docker Desktop mounts (/c/, etc.)

Key Features:
- Automatic workspace root detection
- Smart path resolution with multiple fallback strategies
- Clear error messages with actionable suggestions
- Docker volume mount recommendations
"""

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import cast

logger = logging.getLogger(__name__)

# [20251215_REFACTOR] Remove unused path helper imports (PureWindowsPath/PurePosixPath) for lint compliance.


@dataclass
class PathResolutionResult:
    """Result of path resolution attempt."""

    resolved_path: str | None
    success: bool
    attempted_paths: list[str]
    suggestion: str | None = None
    error_message: str | None = None


class PathResolver:
    """
    Intelligent path resolver for file-based operations.

    Handles path resolution across different deployment contexts:
    - Local filesystem
    - Docker containers
    - Remote servers
    - Various workspace structures

    [20251214_FEATURE] Core path resolution engine for v1.5.3.
    """

    def __init__(
        self,
        workspace_roots: list[str] | None = None,
        enable_docker_detection: bool = True,
    ):
        """
        Initialize PathResolver.

        Args:
            workspace_roots: List of potential workspace root directories.
                           If None, uses common defaults.
            enable_docker_detection: Whether to detect Docker environment
                                   and provide Docker-specific suggestions.
        """
        self.workspace_roots = workspace_roots or self._detect_workspace_roots()
        self.enable_docker_detection = enable_docker_detection
        self.is_docker = self._is_running_in_docker()
        self.path_cache = {}  # Cache for resolved paths

    def _detect_workspace_roots(self) -> list[str]:
        """
        Detect potential workspace root directories.

        [20251214_FEATURE] Auto-detection of workspace roots

        Returns:
            List of directories to search for files, in priority order.
        """
        roots = []

        # Current working directory (highest priority)
        roots.append(os.getcwd())

        # Common Docker mount points
        if os.path.exists("/workspace"):
            roots.append("/workspace")
        if os.path.exists("/app/code"):
            roots.append("/app/code")
        if os.path.exists("/app"):
            roots.append("/app")

        # User home directory projects
        home = os.path.expanduser("~")
        projects_dir = os.path.join(home, "projects")
        if os.path.exists(projects_dir):
            roots.append(projects_dir)

        # Environment variable hints
        if "WORKSPACE_ROOT" in os.environ:
            roots.insert(0, os.environ["WORKSPACE_ROOT"])
        if "PROJECT_ROOT" in os.environ:
            roots.insert(0, os.environ["PROJECT_ROOT"])

        # Remove duplicates while preserving order
        seen = set()
        unique_roots = []
        for root in roots:
            normalized = os.path.normpath(root)
            if normalized not in seen:
                seen.add(normalized)
                unique_roots.append(normalized)

        logger.debug(f"Detected workspace roots: {unique_roots}")
        return unique_roots

    def _is_running_in_docker(self) -> bool:
        """
        Detect if code is running inside a Docker container.

        [20251214_FEATURE] Docker environment detection

        Returns:
            True if running in Docker, False otherwise.
        """
        # Check for .dockerenv file
        if os.path.exists("/.dockerenv"):
            return True

        # Check cgroup for docker
        try:
            with open("/proc/1/cgroup") as f:
                return "docker" in f.read() or "containerd" in f.read()
        except (FileNotFoundError, PermissionError):
            pass

        return False

    def _parse_windows_path(self, path: str) -> tuple[str, str] | None:
        r"""
        Parse a Windows-style path and extract drive letter and relative path.

        [20251215_FEATURE] v2.0.0 - Windows path parsing

        Handles formats:
        - C:\\Users\\... (backslash)
        - C:/Users/... (forward slash)
        - c:\\users\\... (lowercase drive)

        Args:
            path: Path string to parse

        Returns:
            Tuple of (drive_letter, relative_path) or None if not a Windows path
        """
        # Match Windows drive letter pattern: C:\ or C:/
        win_match = re.match(r"^([A-Za-z]):[/\\](.*)$", path)
        if win_match:
            drive = win_match.group(1).lower()
            rel_path = win_match.group(2).replace("\\", "/")
            return (drive, rel_path)
        return None

    def _translate_windows_path(self, path: str) -> list[str]:
        """
        Translate a Windows path to potential Linux/Docker equivalents.

        [20251215_FEATURE] v2.0.0 - Windows to Linux path translation

        Generates candidate paths for:
        - WSL-style mounts: /mnt/c/Users/...
        - Docker Desktop mounts: /c/Users/...
        - Custom WINDOWS_DRIVE_MAP mappings
        - Workspace-relative paths

        Args:
            path: Windows path to translate

        Returns:
            List of candidate Linux paths to try
        """
        candidates = []
        parsed = self._parse_windows_path(path)

        if not parsed:
            return candidates

        drive, rel_path = parsed

        # Strategy 1: WSL-style mount (/mnt/c/...)
        candidates.append(f"/mnt/{drive}/{rel_path}")

        # Strategy 2: Docker Desktop mount (/c/...)
        candidates.append(f"/{drive}/{rel_path}")

        # Strategy 3: Custom drive mapping from environment
        # Format: WINDOWS_DRIVE_MAP="C=/data,D=/backup"
        drive_map = os.environ.get("WINDOWS_DRIVE_MAP", "")
        if drive_map:
            for mapping in drive_map.split(","):
                if "=" in mapping:
                    map_drive, map_path = mapping.split("=", 1)
                    if map_drive.strip().upper() == drive.upper():
                        candidates.append(f"{map_path.strip()}/{rel_path}")

        # Strategy 4: Relative to workspace roots (strip drive, use relative)
        for root in self.workspace_roots:
            candidates.append(f"{root}/{rel_path}")

        logger.debug(f"Windows path '{path}' translated to candidates: {candidates}")
        return candidates

    def resolve(self, path: str, project_root: str | None = None) -> str:
        """
        Resolve a path to its accessible location.

        [20251214_FEATURE] Main path resolution with comprehensive fallback

        Args:
            path: Path to resolve (absolute, relative, or basename)
            project_root: Optional explicit project root to try first

        Returns:
            Resolved absolute path

        Raises:
            FileNotFoundError: If path cannot be resolved with helpful suggestions
        """
        # [20251214_BUGFIX] Reject empty or whitespace-only paths to avoid platform-specific normalization quirks
        if not path or not str(path).strip():
            raise FileNotFoundError("Cannot access file: empty or whitespace-only path")

        # Check cache first
        cache_key = (path, project_root)
        if cache_key in self.path_cache:
            cached = self.path_cache[cache_key]
            if os.path.exists(cached):
                return cached

        result = self._attempt_resolution(path, project_root)

        if result.success:
            # Cache successful resolution
            # [20251220_BUGFIX] Type narrowing: if result.success is True, resolved_path is guaranteed to be str
            self.path_cache[cache_key] = cast(str, result.resolved_path)
            return cast(str, result.resolved_path)
        else:
            # Raise with helpful error message
            raise FileNotFoundError(self._format_error_message(path, result))

    def _attempt_resolution(self, path: str, project_root: str | None) -> PathResolutionResult:
        """
        Attempt to resolve path with multiple strategies.

        [20251214_FEATURE] Multi-strategy path resolution
        [20251215_FEATURE] v2.0.0 - Added Windows path translation

        Strategies (in order):
        0. Windows path translation (if Windows path detected)
        1. Direct access (absolute path exists)
        2. Relative to explicit project_root
        3. Relative to detected workspace roots
        4. Basename search in workspace roots (recursive)
        5. Parent directory search (for relative paths with subdirs)

        Args:
            path: Path to resolve
            project_root: Optional explicit project root

        Returns:
            PathResolutionResult with resolution details
        """
        attempted_paths = []

        # [20251215_FEATURE] Strategy 0: Windows path handling
        # Detect Windows-style paths (C:\... or C:/...) and handle them appropriately
        if self._parse_windows_path(path):
            # First, try the original Windows path directly (works on Windows)
            original_windows_path = path.replace("/", os.sep).replace("\\", os.sep)
            if os.path.exists(original_windows_path):
                return PathResolutionResult(
                    resolved_path=os.path.normpath(original_windows_path),
                    success=True,
                    attempted_paths=[original_windows_path],
                )
            attempted_paths.append(original_windows_path)

            # If direct access fails (e.g., running in Docker/Linux), try translations
            windows_candidates = self._translate_windows_path(path)
            for candidate in windows_candidates:
                attempted_paths.append(candidate)
                if os.path.exists(candidate):
                    return PathResolutionResult(
                        resolved_path=os.path.normpath(candidate),
                        success=True,
                        attempted_paths=attempted_paths,
                    )
            # Continue with other strategies using the relative portion
            parsed = self._parse_windows_path(path)
            if parsed:
                _, rel_path = parsed
                # Try the relative path with other strategies
                path = rel_path

        path_obj = Path(path)

        # Strategy 1: Direct access (absolute path)
        if path_obj.is_absolute() and path_obj.exists():
            return PathResolutionResult(
                resolved_path=str(path_obj.resolve()),
                success=True,
                attempted_paths=attempted_paths + [str(path_obj)],
            )
        attempted_paths.append(str(path_obj))

        # Strategy 2: Relative to explicit project_root
        if project_root:
            candidate = Path(project_root) / path
            if candidate.exists():
                return PathResolutionResult(
                    resolved_path=str(candidate.resolve()),
                    success=True,
                    attempted_paths=attempted_paths + [str(candidate)],
                )
            attempted_paths.append(str(candidate))

        # Strategy 3: Relative to workspace roots
        for root in self.workspace_roots:
            candidate = Path(root) / path
            if candidate.exists():
                return PathResolutionResult(
                    resolved_path=str(candidate.resolve()),
                    success=True,
                    attempted_paths=attempted_paths + [str(candidate)],
                )
            attempted_paths.append(str(candidate))

        # Strategy 4: Basename search (for simple filenames)
        if not os.path.dirname(path):
            # It's just a filename, search workspace roots
            for root in self.workspace_roots:
                found = self._find_file_in_tree(root, os.path.basename(path))
                if found:
                    return PathResolutionResult(
                        resolved_path=found,
                        success=True,
                        attempted_paths=attempted_paths + [found],
                    )

        # Strategy 5: Parent directory hints
        if os.path.dirname(path):
            dirname = os.path.dirname(path)
            basename = os.path.basename(path)
            for root in self.workspace_roots:
                # Try finding the directory structure
                candidate = Path(root) / dirname / basename
                if candidate.exists():
                    return PathResolutionResult(
                        resolved_path=str(candidate.resolve()),
                        success=True,
                        attempted_paths=attempted_paths + [str(candidate)],
                    )
                attempted_paths.append(str(candidate))

        # All strategies failed
        return PathResolutionResult(
            resolved_path=None,
            success=False,
            attempted_paths=attempted_paths,
            suggestion=self._generate_suggestion(path, attempted_paths),
        )

    def _find_file_in_tree(self, root: str, filename: str, max_depth: int = 5) -> str | None:
        """
        Search for a file in directory tree.

        [20251214_FEATURE] Recursive file search with depth limit

        Args:
            root: Root directory to search
            filename: Filename to find
            max_depth: Maximum directory depth to search

        Returns:
            Absolute path if found, None otherwise
        """
        try:
            root_path = Path(root)
            if not root_path.exists():
                return None

            # Use rglob with depth limitation
            for path in root_path.rglob(filename):
                # Calculate depth
                relative = path.relative_to(root_path)
                depth = len(relative.parts) - 1
                if depth <= max_depth and path.is_file():
                    return str(path.resolve())
        except (PermissionError, OSError):
            pass

        return None

    def _generate_suggestion(self, path: str, attempted_paths: list[str]) -> str:
        """
        Generate helpful suggestion for failed path resolution.

        [20251214_FEATURE] Docker-aware error suggestions
        [20251215_FEATURE] v2.0.0 - Windows path suggestions

        Args:
            path: Original path that failed
            attempted_paths: List of paths that were tried

        Returns:
            Helpful suggestion string
        """
        suggestions = []
        is_windows_path = self._parse_windows_path(path) is not None

        if self.is_docker:
            # Docker-specific suggestions
            suggestions.append(
                "Running in Docker: Mount your project directory with:\n"
                "  docker run -v /path/to/your/project:/workspace ... <image>"
            )

            # [20251215_FEATURE] Windows-specific Docker suggestions
            if is_windows_path:
                parsed = self._parse_windows_path(path)
                if parsed:
                    drive, rel_path = parsed
                    parent = os.path.dirname(rel_path) if "/" in rel_path else ""
                    suggestions.append(
                        f"\nWindows path detected. For Docker Desktop on Windows:\n"
                        f"  docker run -v {drive.upper()}:/{parent}:/workspace ... <image>\n"
                        f"  Or use WSL path: /mnt/{drive}/{parent}"
                    )
                    suggestions.append(
                        f"\nYou can also set WINDOWS_DRIVE_MAP environment variable:\n"
                        f"  -e WINDOWS_DRIVE_MAP='{drive.upper()}=/workspace'"
                    )
            elif os.path.isabs(path):
                parent = os.path.dirname(path)
                suggestions.append(f"  docker run -v {parent}:/workspace ... <image>")

        else:
            # Local development suggestions
            if is_windows_path:
                # [20251215_FEATURE] Windows local development suggestions
                suggestions.append(
                    "Windows path detected but file not accessible.\n"
                    "If running in WSL, the path should be accessible at:\n"
                )
                parsed = self._parse_windows_path(path)
                if parsed:
                    drive, rel_path = parsed
                    suggestions.append(f"  /mnt/{drive}/{rel_path}")
            else:
                suggestions.append("Ensure the file exists and use an absolute path, or place it in:\n")
                for root in self.workspace_roots[:3]:  # Top 3 roots
                    suggestions.append(f"  - {root}")

        # Add workspace root hint
        suggestions.append(f"\nCurrent workspace roots: {', '.join(self.workspace_roots)}")
        suggestions.append("Set WORKSPACE_ROOT environment variable to specify custom root.")

        return "\n".join(suggestions)

    def _format_error_message(self, path: str, result: PathResolutionResult) -> str:
        """
        Format comprehensive error message.

        [20251214_FEATURE] User-friendly error messages

        Args:
            path: Original path that failed
            result: Resolution result with details

        Returns:
            Formatted error message
        """
        # [20251214_BUGFIX] Include explicit 'not found' wording for compatibility with callers/tests
        lines = [
            f"Cannot access file: {path} (not found)",
            "",
            f"Attempted locations ({len(result.attempted_paths)}):",
        ]

        # Show up to 5 attempted paths
        for attempted in result.attempted_paths[:5]:
            lines.append(f"  [FAIL] {attempted}")

        if len(result.attempted_paths) > 5:
            lines.append(f"  ... and {len(result.attempted_paths) - 5} more")

        if result.suggestion:
            lines.append("")
            lines.append("Suggestion:")
            lines.append(result.suggestion)

        return "\n".join(lines)

    def validate_paths(self, paths: list[str], project_root: str | None = None) -> tuple[list[str], list[str]]:
        """
        Validate multiple paths and return accessible/inaccessible lists.

        [20251214_FEATURE] Batch path validation

        Args:
            paths: List of paths to validate
            project_root: Optional project root

        Returns:
            Tuple of (accessible_paths, inaccessible_paths)
        """
        accessible = []
        inaccessible = []

        for path in paths:
            try:
                resolved = self.resolve(path, project_root)
                accessible.append(resolved)
            except FileNotFoundError:
                inaccessible.append(path)

        return accessible, inaccessible

    def clear_cache(self):
        """Clear the path resolution cache."""
        self.path_cache.clear()
        logger.debug("Path resolution cache cleared")


# Global singleton instance for convenience
_default_resolver: PathResolver | None = None


def get_default_resolver() -> PathResolver:
    """
    Get or create the default PathResolver instance.

    [20251214_FEATURE] Singleton accessor for easy integration

    Returns:
        Default PathResolver instance
    """
    global _default_resolver
    if _default_resolver is None:
        _default_resolver = PathResolver()
    return _default_resolver


def resolve_path(path: str, project_root: str | None = None) -> str:
    """
    Convenience function for path resolution using default resolver.

    [20251214_FEATURE] Simple API for path resolution

    Args:
        path: Path to resolve
        project_root: Optional project root

    Returns:
        Resolved absolute path

    Raises:
        FileNotFoundError: If path cannot be resolved
    """
    return get_default_resolver().resolve(path, project_root)
