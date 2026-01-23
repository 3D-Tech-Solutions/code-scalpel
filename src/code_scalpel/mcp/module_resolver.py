"""
Module Path Resolver - Map language module names to file paths.

[20251216_FEATURE] v2.0.2 - Resource template support for code:/// URIs.

This module provides resolution of module names to file paths across different
programming languages, enabling parameterized URI access to code symbols.
"""

from pathlib import Path


def resolve_module_path(language: str, module: str, project_root: Path) -> Path | None:
    """
    Resolve a module name to a file path for a given language.

    [20251216_FEATURE] v2.0.2 - Multi-language module resolution.

    Args:
        language: Programming language ("python", "javascript", "typescript", "java")
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
    else:
        return None


def _resolve_python_module(module: str, project_root: Path) -> Path | None:
    """
    Resolve Python module name to file path.

    Patterns:
    - utils -> utils.py
    - utils.math -> utils/math.py
    - services.auth -> services/auth.py
    """
    # Replace dots with path separators
    module_path = module.replace(".", "/")

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


def _resolve_javascript_module(module: str, project_root: Path) -> Path | None:
    """
    Resolve JavaScript module name to file path.

    Patterns:
    - utils -> utils.js or utils/index.js
    - components/Button -> components/Button.js or components/Button/index.js
    - lib/helpers -> lib/helpers.js or lib/helpers/index.js
    """
    # Convert module notation to path
    module_path = module.replace(".", "/")

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


def _resolve_typescript_module(module: str, project_root: Path) -> Path | None:
    """
    Resolve TypeScript module name to file path.

    Patterns:
    - utils -> utils.ts or utils/index.ts
    - components/UserCard -> components/UserCard.tsx
    - lib/api -> lib/api.ts or lib/api/index.ts
    """
    # Convert module notation to path
    module_path = module.replace(".", "/")

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


def _resolve_java_module(module: str, project_root: Path) -> Path | None:
    """
    Resolve Java module name (fully qualified class name) to file path.

    Patterns:
    - services.AuthService -> services/AuthService.java
    - com.example.User -> com/example/User.java
    - utils.Calculator -> utils/Calculator.java
    """
    # Replace dots with path separators
    module_path = module.replace(".", "/")

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
