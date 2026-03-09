"""
Module Path Resolver - Map language module names to file paths.

[20251216_FEATURE] v2.0.2 - Resource template support for code:/// URIs.
[20260306_FEATURE] Extended code:/// resolution to the full file-backed
polyglot language set used by extract_code resources.

This module provides resolution of module names to file paths across different
programming languages, enabling parameterized URI access to code symbols.
"""

from pathlib import Path
from typing import Optional


def _normalize_module_path(module: str) -> str:
    """Normalize language module notation into a relative path fragment."""
    return module.replace("::", "/").replace(".", "/")


def _resolve_by_extensions(
    module: str,
    project_root: Path,
    extensions: tuple[str, ...],
    *,
    allow_index: bool = False,
    search_roots: tuple[str, ...] = ("", "src"),
) -> Optional[Path]:
    """Resolve a module using a small set of file extensions and roots."""
    module_path = _normalize_module_path(module)

    for root in search_roots:
        base = project_root / root if root else project_root

        for extension in extensions:
            candidate = base / f"{module_path}{extension}"
            if candidate.exists():
                return candidate

        if allow_index:
            for extension in extensions:
                candidate = base / module_path / f"index{extension}"
                if candidate.exists():
                    return candidate

    return None


def resolve_module_path(
    language: str, module: str, project_root: Path
) -> Optional[Path]:
    """
    Resolve a module name to a file path for a given language.

    [20251216_FEATURE] v2.0.2 - Multi-language module resolution.

    Args:
        language: Programming language
        module: Module name (e.g., "utils", "components/UserCard", "services.auth")
        project_root: Project root directory

    Returns:
        Resolved file path, or None if not found

    Examples:
        >>> resolve_module_path("python", "utils", Path("/project"))
        Path("/project/utils.py")

        >>> resolve_module_path("typescript", "components/UserCard", Path("/project"))
        Path("/project/components/UserCard.tsx")

        >>> resolve_module_path("java", "services.AuthService", Path("/project"))
        Path("/project/services/AuthService.java")
    """
    language = language.lower()

    if language == "python":
        return _resolve_python_module(module, project_root)
    elif language in ("javascript", "js"):
        return _resolve_javascript_module(module, project_root)
    elif language in ("typescript", "ts"):
        return _resolve_typescript_module(module, project_root)
    elif language == "java":
        return _resolve_java_module(module, project_root)
    elif language in ("c",):
        return _resolve_c_module(module, project_root)
    elif language in ("cpp", "c++", "cc", "cxx"):
        return _resolve_cpp_module(module, project_root)
    elif language in ("csharp", "cs"):
        return _resolve_csharp_module(module, project_root)
    elif language == "go":
        return _resolve_go_module(module, project_root)
    elif language in ("kotlin", "kt"):
        return _resolve_kotlin_module(module, project_root)
    elif language == "php":
        return _resolve_php_module(module, project_root)
    elif language in ("ruby", "rb"):
        return _resolve_ruby_module(module, project_root)
    elif language == "swift":
        return _resolve_swift_module(module, project_root)
    elif language == "rust":
        return _resolve_rust_module(module, project_root)
    else:
        return None


def _resolve_python_module(module: str, project_root: Path) -> Optional[Path]:
    """
    Resolve Python module name to file path.

    Patterns:
    - utils -> utils.py
    - utils.math -> utils/math.py
    - services.auth -> services/auth.py
    """
    # Replace dots with path separators
    module_path = _normalize_module_path(module)

    # Try direct file
    candidate = project_root / f"{module_path}.py"
    if candidate.exists():
        return candidate

    # Try package __init__.py
    candidate = project_root / module_path / "__init__.py"
    if candidate.exists():
        return candidate

    # Try in src/ directory
    candidate = project_root / "src" / f"{module_path}.py"
    if candidate.exists():
        return candidate

    candidate = project_root / "src" / module_path / "__init__.py"
    if candidate.exists():
        return candidate

    return None


def _resolve_javascript_module(module: str, project_root: Path) -> Optional[Path]:
    """
    Resolve JavaScript module name to file path.

    Patterns:
    - utils -> utils.js or utils/index.js
    - components/Button -> components/Button.js or components/Button/index.js
    - lib/helpers -> lib/helpers.js or lib/helpers/index.js
    """
    # Convert module notation to path
    module_path = _normalize_module_path(module)

    # Try direct .js file
    candidate = project_root / f"{module_path}.js"
    if candidate.exists():
        return candidate

    # Try .jsx file (React)
    candidate = project_root / f"{module_path}.jsx"
    if candidate.exists():
        return candidate

    # Try index.js
    candidate = project_root / module_path / "index.js"
    if candidate.exists():
        return candidate

    # Try index.jsx
    candidate = project_root / module_path / "index.jsx"
    if candidate.exists():
        return candidate

    # Try in src/
    candidate = project_root / "src" / f"{module_path}.js"
    if candidate.exists():
        return candidate

    candidate = project_root / "src" / f"{module_path}.jsx"
    if candidate.exists():
        return candidate

    candidate = project_root / "src" / module_path / "index.js"
    if candidate.exists():
        return candidate

    return None


def _resolve_typescript_module(module: str, project_root: Path) -> Optional[Path]:
    """
    Resolve TypeScript module name to file path.

    Patterns:
    - utils -> utils.ts or utils/index.ts
    - components/UserCard -> components/UserCard.tsx
    - lib/api -> lib/api.ts or lib/api/index.ts
    """
    # Convert module notation to path
    module_path = _normalize_module_path(module)

    # Try direct .ts file
    candidate = project_root / f"{module_path}.ts"
    if candidate.exists():
        return candidate

    # Try .tsx file (React TypeScript)
    candidate = project_root / f"{module_path}.tsx"
    if candidate.exists():
        return candidate

    # Try index.ts
    candidate = project_root / module_path / "index.ts"
    if candidate.exists():
        return candidate

    # Try index.tsx
    candidate = project_root / module_path / "index.tsx"
    if candidate.exists():
        return candidate

    # Try in src/
    candidate = project_root / "src" / f"{module_path}.ts"
    if candidate.exists():
        return candidate

    candidate = project_root / "src" / f"{module_path}.tsx"
    if candidate.exists():
        return candidate

    candidate = project_root / "src" / module_path / "index.ts"
    if candidate.exists():
        return candidate

    candidate = project_root / "src" / module_path / "index.tsx"
    if candidate.exists():
        return candidate

    return None


def _resolve_java_module(module: str, project_root: Path) -> Optional[Path]:
    """
    Resolve Java module name (fully qualified class name) to file path.

    Patterns:
    - services.AuthService -> services/AuthService.java
    - com.example.User -> com/example/User.java
    - utils.Calculator -> utils/Calculator.java
    """
    # Replace dots with path separators
    module_path = _normalize_module_path(module)

    # Try direct .java file
    candidate = project_root / f"{module_path}.java"
    if candidate.exists():
        return candidate

    # Try in src/
    candidate = project_root / "src" / f"{module_path}.java"
    if candidate.exists():
        return candidate

    # Try in src/main/java/ (Maven/Gradle standard)
    candidate = project_root / "src" / "main" / "java" / f"{module_path}.java"
    if candidate.exists():
        return candidate

    return None


def _resolve_c_module(module: str, project_root: Path) -> Optional[Path]:
    """Resolve C translation unit or header paths."""
    return _resolve_by_extensions(
        module,
        project_root,
        (".c", ".h"),
        search_roots=("", "src", "include"),
    )


def _resolve_cpp_module(module: str, project_root: Path) -> Optional[Path]:
    """Resolve C++ source or header paths."""
    return _resolve_by_extensions(
        module,
        project_root,
        (".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx", ".h"),
        search_roots=("", "src", "include"),
    )


def _resolve_csharp_module(module: str, project_root: Path) -> Optional[Path]:
    """Resolve C# modules to .cs files."""
    return _resolve_by_extensions(
        module,
        project_root,
        (".cs",),
        search_roots=("", "src"),
    )


def _resolve_go_module(module: str, project_root: Path) -> Optional[Path]:
    """Resolve Go modules to .go files."""
    return _resolve_by_extensions(
        module,
        project_root,
        (".go",),
        search_roots=("", "src", "cmd", "pkg", "internal"),
    )


def _resolve_kotlin_module(module: str, project_root: Path) -> Optional[Path]:
    """Resolve Kotlin modules to .kt or .kts files."""
    return _resolve_by_extensions(
        module,
        project_root,
        (".kt", ".kts"),
        search_roots=("", "src", "src/main/kotlin", "src/test/kotlin"),
    )


def _resolve_php_module(module: str, project_root: Path) -> Optional[Path]:
    """Resolve PHP modules to .php family files."""
    return _resolve_by_extensions(
        module,
        project_root,
        (".php", ".phtml", ".php5", ".php7"),
        allow_index=True,
        search_roots=("", "src", "app"),
    )


def _resolve_ruby_module(module: str, project_root: Path) -> Optional[Path]:
    """Resolve Ruby modules to .rb or related files."""
    return _resolve_by_extensions(
        module,
        project_root,
        (".rb", ".rake"),
        allow_index=True,
        search_roots=("", "lib", "app", "src"),
    )


def _resolve_swift_module(module: str, project_root: Path) -> Optional[Path]:
    """Resolve Swift modules to .swift files."""
    return _resolve_by_extensions(
        module,
        project_root,
        (".swift",),
        search_roots=("", "Sources", "src"),
    )


def _resolve_rust_module(module: str, project_root: Path) -> Optional[Path]:
    """Resolve Rust modules to .rs files."""
    return _resolve_by_extensions(
        module,
        project_root,
        (".rs",),
        allow_index=True,
        search_roots=("", "src", "examples"),
    )


def get_mime_type(language: str) -> str:
    """
    Get MIME type for a programming language.

    [20251216_FEATURE] v2.0.2 - MIME types for resource templates.

    Args:
        language: Programming language

    Returns:
        MIME type string
    """
    mime_types = {
        "python": "text/x-python",
        "javascript": "text/javascript",
        "js": "text/javascript",
        "typescript": "text/x-typescript",
        "ts": "text/x-typescript",
        "tsx": "text/x-tsx",
        "jsx": "text/x-jsx",
        "java": "text/x-java",
        "c": "text/x-c",
        "cpp": "text/x-c++src",
        "csharp": "text/x-csharp",
        "cs": "text/x-csharp",
        "go": "text/x-go",
        "kotlin": "text/x-kotlin",
        "kt": "text/x-kotlin",
        "php": "application/x-php",
        "ruby": "text/x-ruby",
        "rb": "text/x-ruby",
        "swift": "text/x-swift",
        "rust": "text/x-rustsrc",
    }

    return mime_types.get(language.lower(), "text/plain")


# [20251220_TODO] Add package manager aware module resolution:
#     - Detect package.json, pyproject.toml, pom.xml to understand project structure
#     - Support workspace/monorepo module resolution (npm workspaces, poetry groups)
#     - Resolve node_modules/@scoped/package structure
#     - Handle virtual imports (barrel exports, path aliases in tsconfig.json)

# [20251220_TODO] Add cache for resolved module paths:
#     - Cache resolution results to avoid repeated filesystem lookups
#     - Invalidate cache on file system changes
#     - Use mtime/hash to detect stale entries

# [20251220_TODO] Add symlink resolution:
#     - Follow symlinks when resolving paths
#     - Detect symlink cycles to prevent infinite loops
#     - Handle npm link and similar symlink patterns
