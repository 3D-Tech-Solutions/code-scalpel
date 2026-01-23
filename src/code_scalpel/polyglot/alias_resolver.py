from __future__ import annotations

import json
import re
from pathlib import Path


class AliasResolver:
    """
    [20251216_FEATURE] Resolver for module aliases from various config files.

    Supports:
    - tsconfig.json paths
    - webpack.config.js resolve.alias
    - vite.config.ts resolve.alias

    Example:
        >>> resolver = AliasResolver("/project/root")
        >>> resolver.resolve("@ui/Button")
        '/project/root/src/ui/Button'
    """

    def __init__(self, project_root: str | Path):
        """
        Initialize the alias resolver.

        Args:
            project_root: Root directory of the project

        [20251216_FEATURE] Load aliases from project config files
        """
        self.project_root = Path(project_root).resolve()
        self.aliases: dict[str, str] = {}
        self._load_aliases()

    def _load_aliases(self) -> None:
        """
        Load aliases from all available config files.

        [20251216_FEATURE] Multi-source alias loading
        """
        # Load from tsconfig.json
        self._load_tsconfig_aliases()

        # Load from webpack.config.js
        self._load_webpack_aliases()

        # Load from vite.config.ts
        self._load_vite_aliases()

    def _load_tsconfig_aliases(self) -> None:
        """
        Load path aliases from tsconfig.json.

        Example tsconfig.json:
        {
          "compilerOptions": {
            "paths": {
              "@ui/*": ["./src/ui/*"],
              "@data/*": ["./packages/data/src/*"],
              "@utils": ["./src/common/utils"]
            }
          }
        }

        [20251216_FEATURE] TypeScript path alias resolution
        """
        tsconfig_path = self.project_root / "tsconfig.json"
        if not tsconfig_path.exists():
            return

        try:
            with open(tsconfig_path, encoding="utf-8") as f:
                config = json.load(f)

            paths = config.get("compilerOptions", {}).get("paths", {})
            base_url = config.get("compilerOptions", {}).get("baseUrl", ".")

            for alias, targets in paths.items():
                if not targets:
                    continue

                # Use the first target
                target = targets[0]

                # Remove wildcard from alias and target
                clean_alias = alias.rstrip("/*")
                clean_target = target.rstrip("/*")

                # Resolve target relative to baseUrl
                if base_url:
                    resolved_target = str((self.project_root / base_url / clean_target).resolve())
                else:
                    resolved_target = str((self.project_root / clean_target).resolve())

                self.aliases[clean_alias] = resolved_target

        except (json.JSONDecodeError, FileNotFoundError, KeyError):
            # Log error but don't fail - just skip tsconfig aliases
            pass

    def _load_webpack_aliases(self) -> None:
        """
        Load aliases from webpack.config.js.

        Example webpack.config.js:
        module.exports = {
          resolve: {
            alias: {
              '@ui': path.resolve(__dirname, 'src/ui'),
              '@data': path.resolve(__dirname, 'packages/data/src')
            }
          }
        };

        [20251216_FEATURE] Webpack alias resolution

        Note: This is a simple regex-based parser. For complex configs,
        consider using a JavaScript engine.
        """
        webpack_paths = [
            self.project_root / "webpack.config.js",
            self.project_root / "webpack.config.ts",
        ]

        for webpack_path in webpack_paths:
            if not webpack_path.exists():
                continue

            try:
                with open(webpack_path, encoding="utf-8") as f:
                    content = f.read()

                # Extract alias definitions using regex
                # Pattern: '@alias': path.resolve(..., 'target')
                alias_pattern = re.compile(
                    r"['\"](@[\w/]+)['\"]\s*:\s*(?:path\.resolve|require\.resolve)\([^,]+,\s*['\"]([^'\"]+)['\"]\)"
                )

                for match in alias_pattern.finditer(content):
                    alias = match.group(1)
                    target = match.group(2)

                    # Resolve target
                    resolved_target = str((self.project_root / target).resolve())
                    self.aliases[alias] = resolved_target

            except (FileNotFoundError, Exception):
                # Log error but don't fail
                pass

    def _load_vite_aliases(self) -> None:
        """
        Load aliases from vite.config.ts.

        Example vite.config.ts:
        export default {
          resolve: {
            alias: {
              '@ui': '/src/ui',
              '@data': '/packages/data/src'
            }
          }
        };

        [20251216_FEATURE] Vite alias resolution
        """
        vite_paths = [
            self.project_root / "vite.config.ts",
            self.project_root / "vite.config.js",
        ]

        for vite_path in vite_paths:
            if not vite_path.exists():
                continue

            try:
                with open(vite_path, encoding="utf-8") as f:
                    content = f.read()

                # Extract alias definitions using regex
                # Pattern: '@alias': '/target' or '@alias': './target'
                alias_pattern = re.compile(r"['\"](@[\w/]+)['\"]\s*:\s*['\"]([^'\"]+)['\"]\s*[,}]")

                for match in alias_pattern.finditer(content):
                    alias = match.group(1)
                    target = match.group(2)

                    # Remove leading slash if present
                    if target.startswith("/"):
                        target = target[1:]

                    # Resolve target
                    resolved_target = str((self.project_root / target).resolve())
                    self.aliases[alias] = resolved_target

            except (FileNotFoundError, Exception):
                # Log error but don't fail
                pass

    def resolve(self, import_path: str) -> str:
        """
        Resolve an aliased import path to its actual path.

        Args:
            import_path: Import path that may contain aliases (e.g., '@ui/Button')

        Returns:
            Resolved path (e.g., '/project/src/ui/Button')

        [20251216_FEATURE] Alias resolution for imports

        Example:
            >>> resolver.resolve('@ui/components/Button')
            '/project/src/ui/components/Button'

            >>> resolver.resolve('./relative/path')
            './relative/path'  # No change for relative paths
        """
        # Check each alias
        for alias, target in self.aliases.items():
            if import_path.startswith(alias):
                # Replace alias with target
                # Handle both exact matches and sub-paths
                if import_path == alias:
                    return target
                elif import_path.startswith(alias + "/"):
                    suffix = import_path[len(alias) :]
                    return target + suffix

        # No alias matched, return as-is
        return import_path

    def get_all_aliases(self) -> dict[str, str]:
        """
        Get all loaded aliases.

        Returns:
            Dictionary mapping aliases to their resolved paths

        [20251216_FEATURE] Alias inspection
        """
        return self.aliases.copy()

    def has_alias(self, alias: str) -> bool:
        """
        Check if an alias is defined.

        Args:
            alias: Alias to check (e.g., '@ui')

        Returns:
            True if alias is defined

        [20251216_FEATURE] Alias existence check
        """
        return alias in self.aliases

    def resolve_to_file(self, import_path: str, extensions: list[str] | None = None) -> Path | None:
        """
        Resolve an import path to an actual file.

        Args:
            import_path: Import path (may contain aliases)
            extensions: File extensions to try (default: ['.ts', '.tsx', '.js', '.jsx'])

        Returns:
            Path object if file exists, None otherwise

        [20251216_FEATURE] File-aware alias resolution
        """
        if extensions is None:
            extensions = [".ts", ".tsx", ".js", ".jsx", ".json"]

        # Resolve alias
        resolved_path = self.resolve(import_path)

        # If path is relative, can't resolve to file without context
        if resolved_path.startswith("."):
            return None

        path = Path(resolved_path)

        # Try as-is
        if path.exists() and path.is_file():
            return path

        # Try with extensions
        for ext in extensions:
            file_path = path.with_suffix(ext)
            if file_path.exists():
                return file_path

            # Try adding extension (for paths without suffix)
            if not path.suffix:
                file_path = Path(str(path) + ext)
                if file_path.exists():
                    return file_path

        # Try as directory with index file
        if path.is_dir():
            for ext in extensions:
                index_file = path / f"index{ext}"
                if index_file.exists():
                    return index_file

        return None


# [20251216_FEATURE] Convenience function for quick alias resolution
def create_alias_resolver(project_root: str | Path) -> AliasResolver:
    """
    Create an alias resolver for a project.

    Args:
        project_root: Root directory of the project

    Returns:
        Configured AliasResolver instance

    Example:
        >>> resolver = create_alias_resolver("/my/project")
        >>> resolver.resolve("@ui/Button")
        '/my/project/src/ui/Button'
    """
    return AliasResolver(project_root)
