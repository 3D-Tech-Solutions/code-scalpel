"""
Framework Detection - Identify web framework entry points.

[20251226_FEATURE] Detects Next.js, Django, Flask, FastAPI routes and components.

This module identifies framework-specific entry points for web frameworks,
enabling better crawl analysis for Pro and Enterprise tiers.

Supports:
- Next.js: app/ and pages/ directories, server components, route handlers
- Django: urls.py patterns, views, class-based views, management commands
- Flask: @app.route, @blueprint.route decorators, blueprints
- FastAPI: @app.get/@app.post, APIRouter definitions

Usage:
    from code_scalpel.analysis.framework_detector import detect_frameworks

    frameworks = detect_frameworks("/path/to/project")
    for fw_name, routes in frameworks.items():
        print(f"{fw_name}: {len(routes)} routes detected")
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class FrameworkRoute:
    """Detected route or entry point in a framework."""

    framework: str
    file_path: str
    route_pattern: str
    handler_name: str
    handler_type: str  # "function", "class_method", "component"
    line_number: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FrameworkDetectionResult:
    """Result of framework detection."""

    detected_frameworks: set[str]
    routes: list[FrameworkRoute]
    nextjs_pages: list[str]
    django_views: list[str]
    flask_routes: list[str]
    fastapi_routes: list[str]
    generated_files: list[dict[str, str]]  # .pb.py, migrations, etc.
    metadata: dict[str, Any] = field(default_factory=dict)


class FrameworkDetector:
    """Detects web framework entry points and components."""

    def __init__(self, project_root: str | Path):
        """Initialize detector with project root."""
        self.root = Path(project_root)
        self.routes: list[FrameworkRoute] = []
        self.detected_frameworks: set[str] = set()
        self.generated_files: list[dict[str, str]] = []

    def detect(self) -> FrameworkDetectionResult:
        """Run full framework detection across the project."""
        # Detect each framework type
        self._detect_nextjs()
        self._detect_django()
        self._detect_flask()
        self._detect_fastapi()
        self._detect_generated_code()

        # Organize results by type
        nextjs_pages = [r.route_pattern for r in self.routes if r.framework == "next.js"]
        django_views = [r.handler_name for r in self.routes if r.framework == "django"]
        flask_routes = [r.route_pattern for r in self.routes if r.framework == "flask"]
        fastapi_routes = [r.route_pattern for r in self.routes if r.framework == "fastapi"]

        return FrameworkDetectionResult(
            detected_frameworks=self.detected_frameworks,
            routes=self.routes,
            nextjs_pages=nextjs_pages,
            django_views=django_views,
            flask_routes=flask_routes,
            fastapi_routes=fastapi_routes,
            generated_files=self.generated_files,
            metadata={"project_root": str(self.root)},
        )

    def _detect_nextjs(self) -> None:
        """Detect Next.js pages and routes."""
        # Check for package.json with next dependency
        pkg_file = self.root / "package.json"
        if not pkg_file.exists():
            return

        try:
            import json

            content = json.loads(pkg_file.read_text())
            if "next" not in content.get("dependencies", {}) and "next" not in content.get("devDependencies", {}):
                return
        except Exception:
            return

        self.detected_frameworks.add("next.js")

        # Scan for page and route files
        for pattern in ["pages/**/*.{js,jsx,ts,tsx}", "app/**/*.{js,jsx,ts,tsx}"]:
            for py_path in self._glob_pattern(pattern):
                rel_path = py_path.relative_to(self.root)

                # Server components (default in app/ router)
                if "app/" in str(py_path):
                    self.routes.append(
                        FrameworkRoute(
                            framework="next.js",
                            file_path=str(rel_path),
                            route_pattern=self._nextjs_path_to_route(rel_path),
                            handler_name="default_export",
                            handler_type="component",
                            line_number=1,
                            metadata={"is_app_router": True},
                        )
                    )
                else:
                    # pages/ router
                    self.routes.append(
                        FrameworkRoute(
                            framework="next.js",
                            file_path=str(rel_path),
                            route_pattern=self._nextjs_path_to_route(rel_path),
                            handler_name="default_export",
                            handler_type="component",
                            line_number=1,
                            metadata={"is_pages_router": True},
                        )
                    )

    def _detect_django(self) -> None:
        """Detect Django views and URL patterns."""
        # Look for manage.py (Django project marker)
        if not (self.root / "manage.py").exists():
            return

        self.detected_frameworks.add("django")

        # Scan urls.py files for URL patterns
        for urls_file in self.root.rglob("urls.py"):
            try:
                content = urls_file.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(content)
                self._extract_django_urls(tree, urls_file)
            except (SyntaxError, UnicodeDecodeError):
                pass

        # Scan views.py for view functions/classes
        for views_file in self.root.rglob("views.py"):
            try:
                content = views_file.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(content)
                self._extract_django_views(tree, views_file)
            except (SyntaxError, UnicodeDecodeError):
                pass

    def _detect_flask(self) -> None:
        """Detect Flask routes and blueprints."""
        # Look for files importing flask
        for py_file in self.root.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                if "from flask import" not in content and "import flask" not in content:
                    continue

                tree = ast.parse(content)
                self._extract_flask_routes(tree, py_file)
            except (SyntaxError, UnicodeDecodeError):
                pass

        if self.routes and any(r.framework == "flask" for r in self.routes):
            self.detected_frameworks.add("flask")

    def _detect_fastapi(self) -> None:
        """Detect FastAPI routes and routers."""
        # Look for files importing fastapi
        for py_file in self.root.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                if "from fastapi import" not in content and "import fastapi" not in content:
                    continue

                tree = ast.parse(content)
                self._extract_fastapi_routes(tree, py_file)
            except (SyntaxError, UnicodeDecodeError):
                pass

        if self.routes and any(r.framework == "fastapi" for r in self.routes):
            self.detected_frameworks.add("fastapi")

    def _detect_generated_code(self) -> None:
        """Detect auto-generated files to skip or mark."""
        patterns = [
            ("**/*.pb.py", "protobuf"),
            ("**/migrations/*.py", "django_migration"),
            ("**/*.graphql", "graphql_schema"),
            ("**/generated/**/*.py", "build_generated"),
            ("**/dist/**", "build_artifact"),
            ("**/build/**", "build_artifact"),
        ]

        for pattern, gen_type in patterns:
            for file_path in self.root.glob(pattern):
                if file_path.is_file():
                    self.generated_files.append(
                        {
                            "path": str(file_path.relative_to(self.root)),
                            "type": gen_type,
                        }
                    )

    def _extract_django_urls(self, tree: ast.AST, file_path: Path) -> None:
        """Extract Django URL patterns from a urls.py file."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # path(), url(), re_path() calls
                if isinstance(node.func, ast.Name) and node.func.id in (
                    "path",
                    "url",
                    "re_path",
                ):
                    if node.args:
                        # First argument is the pattern
                        pattern_node = node.args[0]
                        if isinstance(pattern_node, ast.Constant):
                            pattern = str(pattern_node.value)
                            # Second argument is usually the view
                            if len(node.args) > 1:
                                handler = self._extract_handler_name(node.args[1])
                                self.routes.append(
                                    FrameworkRoute(
                                        framework="django",
                                        file_path=str(file_path.relative_to(self.root)),
                                        route_pattern=pattern,
                                        handler_name=handler,
                                        handler_type="view",
                                        line_number=node.lineno,
                                    )
                                )

    def _extract_django_views(self, tree: ast.AST, file_path: Path) -> None:
        """Extract Django views (functions and classes)."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # View function
                if "view" in node.name.lower() or node.name.startswith("view_"):
                    self.routes.append(
                        FrameworkRoute(
                            framework="django",
                            file_path=str(file_path.relative_to(self.root)),
                            route_pattern=f"view:{node.name}",
                            handler_name=node.name,
                            handler_type="function",
                            line_number=node.lineno,
                        )
                    )
            elif isinstance(node, ast.ClassDef):
                # Class-based view
                if any(isinstance(base, ast.Name) and "View" in base.id for base in node.bases):
                    self.routes.append(
                        FrameworkRoute(
                            framework="django",
                            file_path=str(file_path.relative_to(self.root)),
                            route_pattern=f"cbv:{node.name}",
                            handler_name=node.name,
                            handler_type="class",
                            line_number=node.lineno,
                        )
                    )

    def _extract_flask_routes(self, tree: ast.AST, file_path: Path) -> None:
        """Extract Flask routes from @app.route and @blueprint.route decorators."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    # @app.route("/path") or @blueprint.route("/path")
                    if isinstance(decorator, ast.Call):
                        if isinstance(decorator.func, ast.Attribute):
                            if decorator.func.attr == "route":
                                if decorator.args:
                                    route_node = decorator.args[0]
                                    if isinstance(route_node, ast.Constant):
                                        pattern = str(route_node.value)
                                        self.routes.append(
                                            FrameworkRoute(
                                                framework="flask",
                                                file_path=str(file_path.relative_to(self.root)),
                                                route_pattern=pattern,
                                                handler_name=node.name,
                                                handler_type="function",
                                                line_number=node.lineno,
                                            )
                                        )

    def _extract_fastapi_routes(self, tree: ast.AST, file_path: Path) -> None:
        """Extract FastAPI routes from @app.get/@app.post decorators and APIRouter."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        if isinstance(decorator.func, ast.Attribute):
                            # @app.get, @app.post, @router.get, etc.
                            method = decorator.func.attr.upper()
                            if method in (
                                "GET",
                                "POST",
                                "PUT",
                                "DELETE",
                                "PATCH",
                                "OPTIONS",
                            ):
                                if decorator.args:
                                    route_node = decorator.args[0]
                                    if isinstance(route_node, ast.Constant):
                                        pattern = str(route_node.value)
                                        self.routes.append(
                                            FrameworkRoute(
                                                framework="fastapi",
                                                file_path=str(file_path.relative_to(self.root)),
                                                route_pattern=pattern,
                                                handler_name=node.name,
                                                handler_type="function",
                                                line_number=node.lineno,
                                                metadata={"method": method},
                                            )
                                        )

    def _nextjs_path_to_route(self, path: Path) -> str:
        """Convert Next.js file path to route pattern."""
        parts = str(path).replace("\\", "/").split("/")

        # Filter to get route parts
        route_parts = []
        for part in parts:
            if part in ("pages", "app"):
                continue
            if part.endswith(".tsx") or part.endswith(".ts") or part.endswith(".jsx") or part.endswith(".js"):
                part = part.rsplit(".", 1)[0]

            # Handle dynamic segments
            if part.startswith("[") and part.endswith("]"):
                route_parts.append(f":{part[1:-1]}")
            elif part == "...slug" or (part.startswith("[") and part.endswith("]")):
                # Catch-all segments
                pass
            else:
                route_parts.append(part)

        return "/" + "/".join(route_parts) if route_parts else "/"

    def _extract_handler_name(self, node: ast.AST) -> str:
        """Extract handler name from an AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        else:
            return "unknown"

    def _glob_pattern(self, pattern: str) -> list[Path]:
        """Glob pattern with wildcard expansion."""
        # Simple implementation - expand glob patterns
        # Convert pattern like "pages/**/*.js" to actual globs
        pattern = pattern.replace("**", "*")
        pattern = pattern.replace("{js,jsx,ts,tsx}", "*(js|jsx|ts|tsx)")

        matches = []
        try:
            matches.extend(self.root.glob(pattern))
        except Exception:
            pass
        return matches


def detect_frameworks(project_root: str | Path) -> FrameworkDetectionResult:
    """Detect web frameworks in a project."""
    detector = FrameworkDetector(project_root)
    return detector.detect()
